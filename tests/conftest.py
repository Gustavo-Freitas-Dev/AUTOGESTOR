import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.dependencies import get_db
from main import app


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def cadastrar(client: TestClient, nome: str, email: str):
    resposta = client.post("/auth/cadastro", json={"nome": nome, "email": email, "senha": "senha123"})
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    return corpo, {"Authorization": f"Bearer {corpo['access_token']}"}


@pytest.fixture()
def dois_usuarios(client):
    a, headers_a = cadastrar(client, "Ana", "ana@example.com")
    b, headers_b = cadastrar(client, "Bruno", "bruno@example.com")
    return (a, headers_a), (b, headers_b)
