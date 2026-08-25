from conftest import cadastrar
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import app.routes.auth as auth_routes
from app.models.usuario_model import Usuario


def _espaco_pessoal(client, headers):
    resposta = client.get("/espacos", headers=headers)
    assert resposta.status_code == 200
    return next(e for e in resposta.json() if e["tipo"] == "PESSOAL")


def test_cadastro_persiste_usuario_em_nova_sessao_e_login_funciona(client, db):
    cadastro, _ = cadastrar(client, "Ana", "persistencia@example.com")
    usuario_id = cadastro["usuario"]["id"]

    engine = db.get_bind()
    with Session(engine) as nova_sessao:
        usuario = nova_sessao.query(Usuario).filter(Usuario.id == usuario_id).first()
        assert usuario is not None
        assert usuario.email == "persistencia@example.com"

    resposta_login = client.post(
        "/auth/login",
        json={"email": "persistencia@example.com", "senha": "senha123"},
    )
    assert resposta_login.status_code == 200
    assert resposta_login.json()["access_token"]


def test_login_normaliza_email_com_maiusculas_e_espacos(client):
    cadastrar(client, "Ana", "usuario@email.com")

    resposta = client.post(
        "/auth/login",
        json={"email": "  USUARIO@EMAIL.COM  ", "senha": "senha123"},
    )

    assert resposta.status_code == 200


def test_login_rejeita_senha_incorreta(client):
    cadastrar(client, "Ana", "senha_errada@example.com")

    resposta = client.post(
        "/auth/login",
        json={"email": "senha_errada@example.com", "senha": "senha-errada"},
    )

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "E-mail ou senha incorretos."


def test_login_rejeita_usuario_inexistente(client):
    resposta = client.post(
        "/auth/login",
        json={"email": "naoexiste@example.com", "senha": "senha123"},
    )

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "E-mail ou senha incorretos."


def test_cadastro_com_erro_de_commit_faz_rollback_e_nao_retorna_token(client, db, monkeypatch):
    original_commit = db.commit
    original_rollback = db.rollback
    rollback_chamado = {"ok": False}

    def commit_falha():
        raise SQLAlchemyError("falha commit")

    def rollback_monitorado():
        rollback_chamado["ok"] = True
        return original_rollback()

    monkeypatch.setattr(db, "commit", commit_falha)
    monkeypatch.setattr(db, "rollback", rollback_monitorado)

    resposta = client.post(
        "/auth/cadastro",
        json={"nome": "Ana", "email": "falha_commit@example.com", "senha": "senha123"},
    )

    monkeypatch.setattr(db, "commit", original_commit)
    monkeypatch.setattr(db, "rollback", original_rollback)

    assert resposta.status_code == 503
    assert resposta.json()["detail"] == "database_unavailable"
    assert rollback_chamado["ok"] is True


def test_login_banco_indisponivel_nao_retorna_senha_incorreta(client, monkeypatch):
    def levantar_falha(*_args, **_kwargs):
        raise auth_routes.AuthServiceUnavailableError("database_unavailable")

    monkeypatch.setattr(auth_routes, "autenticar_usuario", levantar_falha)

    resposta = client.post(
        "/auth/login",
        json={"email": "qualquer@example.com", "senha": "senha123"},
    )

    assert resposta.status_code == 503
    assert resposta.json()["detail"] == "auth_service_unavailable"


def test_hash_permanece_inalterado_apos_movimentacao_edicao_e_espaco(client, db):
    cadastro, headers = cadastrar(client, "Ana", "hash_estavel@example.com")
    usuario_id = cadastro["usuario"]["id"]

    usuario_antes = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    assert usuario_antes is not None
    hash_antes = usuario_antes.senha_hash

    espaco = _espaco_pessoal(client, headers)
    mov = client.post(
        f"/espacos/{espaco['id']}/movimentacoes/",
        json={"tipo": "GANHO", "categoria": "Teste", "descricao": "Criacao", "valor": 100, "data": "2026-08-05"},
        headers=headers,
    )
    assert mov.status_code == 200

    mov_id = mov.json()["id"]
    edicao = client.put(
        f"/espacos/{espaco['id']}/movimentacoes/{mov_id}",
        json={"tipo": "GANHO", "categoria": "Teste", "descricao": "Edicao", "valor": 150, "data": "2026-08-05"},
        headers=headers,
    )
    assert edicao.status_code == 200

    espaco_comp = client.post(
        "/espacos/compartilhados",
        json={"nome": "Casa", "limite_membros": 5},
        headers=headers,
    )
    assert espaco_comp.status_code == 201

    patch_espaco = client.patch(
        f"/espacos/{espaco_comp.json()['id']}",
        json={"nome": "Casa Editada", "codigo_ativo": True, "limite_membros": 6},
        headers=headers,
    )
    assert patch_espaco.status_code == 200

    usuario_depois = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    assert usuario_depois is not None
    assert usuario_depois.senha_hash == hash_antes


def test_login_funciona_apos_reinicializar_cliente(client, db):
    cadastrar(client, "Ana", "reinicio@example.com")

    from app.database.dependencies import get_db
    from main import app

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        from fastapi.testclient import TestClient

        with TestClient(app) as novo_cliente:
            resposta = novo_cliente.post(
                "/auth/login",
                json={"email": "reinicio@example.com", "senha": "senha123"},
            )
            assert resposta.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_config_engine_unificada_usada_nas_rotas():
    from app.database.db import engine

    assert engine is not None
    assert engine.dialect.name in {"sqlite", "postgresql"}


def test_cadastro_gera_hash_uma_unica_vez(client, monkeypatch):
    contador = {"chamadas": 0}
    original_hash = auth_routes.hash_senha

    def hash_monitorado(senha: str):
        contador["chamadas"] += 1
        return original_hash(senha)

    monkeypatch.setattr(auth_routes, "hash_senha", hash_monitorado)

    resposta = client.post(
        "/auth/cadastro",
        json={"nome": "Ana", "email": "hash_once@example.com", "senha": "senha123"},
    )

    assert resposta.status_code == 201
    assert contador["chamadas"] == 1


def test_token_emitido_somente_apos_commit(client, db, monkeypatch):
    estado = {"commit_ok": False}
    original_commit = db.commit
    original_token = auth_routes.criar_access_token

    def commit_monitorado():
        original_commit()
        estado["commit_ok"] = True

    def token_monitorado(payload: dict):
        assert estado["commit_ok"] is True
        return original_token(payload)

    monkeypatch.setattr(db, "commit", commit_monitorado)
    monkeypatch.setattr(auth_routes, "criar_access_token", token_monitorado)

    resposta = client.post(
        "/auth/cadastro",
        json={"nome": "Ana", "email": "token_depois_commit@example.com", "senha": "senha123"},
    )

    assert resposta.status_code == 201
    assert estado["commit_ok"] is True


def test_cadastro_falha_se_conexao_db_indisponivel(client, db, monkeypatch):
    original_connection = db.connection

    def falhar_conexao(*_args, **_kwargs):
        raise SQLAlchemyError("timeout de conexao")

    monkeypatch.setattr(db, "connection", falhar_conexao)

    resposta = client.post(
        "/auth/cadastro",
        json={"nome": "Ana", "email": "falha_conexao@example.com", "senha": "senha123"},
    )

    monkeypatch.setattr(db, "connection", original_connection)

    assert resposta.status_code == 503
    assert resposta.json()["detail"] == "database_unavailable"
