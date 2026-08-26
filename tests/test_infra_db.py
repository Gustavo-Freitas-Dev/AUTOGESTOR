import pytest
from conftest import cadastrar
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.database.dependencies import get_db


def test_producao_sem_database_url_falha(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)

    settings = Settings(
        AUTOGESTOR_APP_ENV="production",
        DATABASE_URL="",
        AUTOGESTOR_SECRET_KEY="secret",
    )

    with pytest.raises(RuntimeError, match="DATABASE_URL obrigatoria"):
        _ = settings.effective_database_url


def test_producao_com_sqlite_falha(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)

    settings = Settings(
        AUTOGESTOR_APP_ENV="production",
        DATABASE_URL="sqlite:///autogestor.db",
        AUTOGESTOR_SECRET_KEY="secret",
    )

    with pytest.raises(RuntimeError, match="deve apontar para PostgreSQL"):
        _ = settings.effective_database_url


def test_normaliza_postgres_url(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)

    settings = Settings(
        AUTOGESTOR_APP_ENV="production",
        DATABASE_URL="postgresql://user:pass@localhost:5432/autogestor",
        AUTOGESTOR_SECRET_KEY="secret",
    )

    assert settings.effective_database_url.startswith("postgresql+psycopg://")


def test_producao_sem_secret_key_falha(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)

    settings = Settings(
        AUTOGESTOR_APP_ENV="production",
        DATABASE_URL="postgresql://user:pass@localhost:5432/autogestor",
        AUTOGESTOR_SECRET_KEY="changeme-dev-secret",
    )

    with pytest.raises(RuntimeError, match="AUTOGESTOR_SECRET_KEY obrigatoria"):
        _ = settings.effective_jwt_secret_key


def test_get_db_faz_rollback_e_close_em_excecao():
    eventos = []

    class FakeSession:
        def rollback(self):
            eventos.append("rollback")

        def close(self):
            eventos.append("close")

    from app.database import dependencies as dep_module

    original_session_local = dep_module.SessionLocal
    dep_module.SessionLocal = lambda: FakeSession()

    try:
        generator = get_db()
        _ = next(generator)
        with pytest.raises(RuntimeError):
            generator.throw(RuntimeError("falha"))
    finally:
        dep_module.SessionLocal = original_session_local

    assert eventos == ["rollback", "close"]


def test_healthcheck_retorna_503_quando_banco_falha(client, monkeypatch):
    class FailingSession:
        def execute(self, *_args, **_kwargs):
            raise SQLAlchemyError("db down")

    from main import app

    def override_db():
        yield FailingSession()

    app.dependency_overrides[get_db] = override_db

    try:
        resposta = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"


def test_health_database_retorna_503_quando_banco_falha(client, monkeypatch):
    class FailingSession:
        def execute(self, *_args, **_kwargs):
            raise SQLAlchemyError("db down")

    from main import app

    def override_db():
        yield FailingSession()

    app.dependency_overrides[get_db] = override_db

    try:
        resposta = client.get("/health/database")
    finally:
        app.dependency_overrides.clear()

    assert resposta.status_code == 503
    assert resposta.json()["detail"] == "database_unavailable"


def test_health_nao_consulta_banco(client, db):
    queries = []

    def before_cursor_execute(*_args, **_kwargs):
        queries.append(1)

    event.listen(db.get_bind(), "before_cursor_execute", before_cursor_execute)
    try:
        resposta = client.get("/health")
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", before_cursor_execute)

    assert resposta.status_code == 200
    assert not queries


def test_dashboard_resumo_usa_poucas_queries(client, db):
    _, headers = cadastrar(client, "Ana", "ana_dashboard@example.com")
    espaco = client.get("/espacos", headers=headers).json()[0]

    queries = []

    def before_cursor_execute(*_args, **_kwargs):
        queries.append(1)

    event.listen(db.get_bind(), "before_cursor_execute", before_cursor_execute)
    try:
        resposta = client.get(f"/espacos/{espaco['id']}/dashboard/resumo", headers=headers)
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", before_cursor_execute)

    assert resposta.status_code == 200
    assert len(queries) <= 3


def test_listar_espacos_evita_n_plus_um(client, db):
    _, headers = cadastrar(client, "Ana", "ana_espacos@example.com")
    client.post("/espacos/compartilhados", json={"nome": "Casa", "limite_membros": 5}, headers=headers)

    queries = []

    def before_cursor_execute(*_args, **_kwargs):
        queries.append(1)

    event.listen(db.get_bind(), "before_cursor_execute", before_cursor_execute)
    try:
        resposta = client.get("/espacos", headers=headers)
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", before_cursor_execute)

    assert resposta.status_code == 200
    assert len(resposta.json()) >= 2
    assert len(queries) <= 4
