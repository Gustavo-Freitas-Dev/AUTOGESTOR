import pytest
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
    import main

    class FailingContext:
        def __enter__(self):
            raise SQLAlchemyError("db down")

        def __exit__(self, exc_type, exc, tb):
            return False

    class FailingEngine:
        def connect(self):
            return FailingContext()

    monkeypatch.setattr(main, "engine", FailingEngine())

    resposta = client.get("/health")
    assert resposta.status_code == 503
    assert resposta.json()["detail"] == "database_unavailable"
