import os
import subprocess
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database.dependencies import get_db
from main import app

TEST_URL_ENV = "AUTOGESTOR_TEST_DATABASE_URL"


def _normalizar_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@contextmanager
def cliente_com_db(session_factory):
    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_fluxo_persistencia_relogin_postgres():
    raw_url = os.getenv(TEST_URL_ENV)
    if not raw_url:
        pytest.skip(f"Defina {TEST_URL_ENV} para rodar integração PostgreSQL")

    if "postgres" not in raw_url:
        pytest.skip("URL de integração não parece PostgreSQL")

    if "test" not in raw_url.lower():
        pytest.skip("Proteção: execute integração apenas em banco de teste")

    db_url = _normalizar_url(raw_url)

    admin_engine = create_engine(db_url, pool_pre_ping=True)
    with admin_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    env = os.environ.copy()
    env["DATABASE_URL"] = raw_url
    env["AUTOGESTOR_APP_ENV"] = "development"
    env.setdefault("AUTOGESTOR_SECRET_KEY", "integration-test-secret")

    subprocess.run(["uv", "run", "alembic", "upgrade", "head"], check=True, env=env)

    engine1 = create_engine(db_url, pool_pre_ping=True)
    Session1 = sessionmaker(bind=engine1, autoflush=False, autocommit=False)

    with cliente_com_db(Session1) as client:
        cadastro = client.post(
            "/auth/cadastro",
            json={"nome": "Ana", "email": "integracao@example.com", "senha": "senha123"},
        )
        assert cadastro.status_code == 201, cadastro.text

        token = cadastro.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        espacos = client.get("/espacos", headers=headers)
        assert espacos.status_code == 200
        espaco = next(e for e in espacos.json() if e["tipo"] == "PESSOAL")

        mov = client.post(
            f"/espacos/{espaco['id']}/movimentacoes/",
            json={"tipo": "GANHO", "categoria": "Teste", "descricao": "Persistencia", "valor": 50, "data": "2026-08-05"},
            headers=headers,
        )
        assert mov.status_code == 200, mov.text

        sair = client.post("/auth/logout", headers=headers)
        assert sair.status_code == 204

    engine1.dispose()

    engine2 = create_engine(db_url, pool_pre_ping=True)
    Session2 = sessionmaker(bind=engine2, autoflush=False, autocommit=False)

    with cliente_com_db(Session2) as client2:
        relogin = client2.post(
            "/auth/login",
            json={"email": "integracao@example.com", "senha": "senha123"},
        )
        assert relogin.status_code == 200, relogin.text

        token2 = relogin.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        espacos2 = client2.get("/espacos", headers=headers2)
        assert espacos2.status_code == 200
        espaco2 = next(e for e in espacos2.json() if e["tipo"] == "PESSOAL")

        lista = client2.get(f"/espacos/{espaco2['id']}/movimentacoes/", headers=headers2)
        assert lista.status_code == 200
        assert any(item["descricao"] == "Persistencia" for item in lista.json())

    engine2.dispose()
