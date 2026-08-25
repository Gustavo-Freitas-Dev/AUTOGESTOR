from datetime import UTC, datetime, timedelta

from conftest import cadastrar
from jose import jwt
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.models.espaco_financeiro import EspacoFinanceiro
from app.models.movimentacao import Movimentacao
from app.models.usuario_model import Usuario


def _espaco_pessoal(client, headers):
    resposta = client.get("/espacos", headers=headers)
    assert resposta.status_code == 200
    return next(e for e in resposta.json() if e["tipo"] == "PESSOAL")


def _criar_movimentacao(client, espaco_id, headers, descricao="Registro inicial"):
    payload = {
        "tipo": "GANHO",
        "categoria": "Teste",
        "descricao": descricao,
        "valor": 123.45,
        "data": "2026-08-05",
    }
    resposta = client.post(f"/espacos/{espaco_id}/movimentacoes/", json=payload, headers=headers)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _token_expirado(usuario_id: int) -> str:
    settings = get_settings()
    payload = {
        "sub": str(usuario_id),
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    return jwt.encode(payload, settings.effective_jwt_secret_key, algorithm=settings.jwt_algorithm)


def test_editar_movimentacao_preserva_usuario_hash_e_login(client, db):
    cadastro, headers = cadastrar(client, "Ana", "ana_regressao@example.com")
    usuario_id = cadastro["usuario"]["id"]
    espaco = _espaco_pessoal(client, headers)

    criada = _criar_movimentacao(client, espaco["id"], headers)

    usuario_antes = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    assert usuario_antes is not None
    hash_antes = usuario_antes.senha_hash

    resposta_edicao = client.put(
        f"/espacos/{espaco['id']}/movimentacoes/{criada['id']}",
        json={
            "tipo": "GANHO",
            "categoria": "Teste",
            "descricao": "Descricao editada",
            "valor": 123.45,
            "data": "2026-08-05",
        },
        headers=headers,
    )

    assert resposta_edicao.status_code == 200, resposta_edicao.text
    assert resposta_edicao.json()["message"] == "Movimentação atualizada com sucesso"

    mov_db = db.query(Movimentacao).filter(Movimentacao.id == criada["id"]).first()
    assert mov_db is not None
    assert mov_db.descricao == "Descricao editada"
    assert mov_db.criado_por_id == usuario_id
    assert mov_db.espaco_id == espaco["id"]

    usuario_depois = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    assert usuario_depois is not None
    assert usuario_depois.senha_hash == hash_antes

    login = client.post(
        "/auth/login",
        json={"email": "ana_regressao@example.com", "senha": "senha123"},
    )
    assert login.status_code == 200, login.text


def test_editar_movimentacao_sem_token_retorna_401(client):
    cadastro, headers = cadastrar(client, "Ana", "ana_sem_token@example.com")
    espaco = _espaco_pessoal(client, headers)
    criada = _criar_movimentacao(client, espaco["id"], headers)

    resposta = client.put(
        f"/espacos/{espaco['id']}/movimentacoes/{criada['id']}",
        json={
            "tipo": "GANHO",
            "categoria": "Teste",
            "descricao": "Sem token",
            "valor": 123.45,
            "data": "2026-08-05",
        },
    )

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "token_missing"


def test_editar_movimentacao_token_invalido_retorna_401(client):
    _, headers = cadastrar(client, "Ana", "ana_token_invalido@example.com")
    espaco = _espaco_pessoal(client, headers)
    criada = _criar_movimentacao(client, espaco["id"], headers)

    resposta = client.put(
        f"/espacos/{espaco['id']}/movimentacoes/{criada['id']}",
        json={
            "tipo": "GANHO",
            "categoria": "Teste",
            "descricao": "Token invalido",
            "valor": 123.45,
            "data": "2026-08-05",
        },
        headers={"Authorization": "Bearer token-invalido"},
    )

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "token_invalid"


def test_editar_movimentacao_token_expirado_retorna_401(client):
    cadastro, headers = cadastrar(client, "Ana", "ana_token_expirado@example.com")
    espaco = _espaco_pessoal(client, headers)
    criada = _criar_movimentacao(client, espaco["id"], headers)

    token_expirado = _token_expirado(cadastro["usuario"]["id"])

    resposta = client.put(
        f"/espacos/{espaco['id']}/movimentacoes/{criada['id']}",
        json={
            "tipo": "GANHO",
            "categoria": "Teste",
            "descricao": "Token expirado",
            "valor": 123.45,
            "data": "2026-08-05",
        },
        headers={"Authorization": f"Bearer {token_expirado}"},
    )

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "token_expired"


def test_editar_movimentacao_inexistente_retorna_404(client):
    _, headers = cadastrar(client, "Ana", "ana_mov_inexistente@example.com")
    espaco = _espaco_pessoal(client, headers)

    resposta = client.put(
        f"/espacos/{espaco['id']}/movimentacoes/9999",
        json={
            "tipo": "GANHO",
            "categoria": "Teste",
            "descricao": "Nao existe",
            "valor": 10,
            "data": "2026-08-05",
        },
        headers=headers,
    )

    assert resposta.status_code == 404


def test_impede_edicao_movimentacao_de_outro_usuario_no_mesmo_espaco(client):
    (_, headers_a), (_, headers_b) = (
        cadastrar(client, "Ana", "ana_outro_usuario@example.com"),
        cadastrar(client, "Bruno", "bruno_outro_usuario@example.com"),
    )

    espaco_compartilhado = client.post(
        "/espacos/compartilhados",
        json={"nome": "Casa", "limite_membros": 5},
        headers=headers_a,
    ).json()

    entrar = client.post(
        "/espacos/entrar",
        json={"codigo": espaco_compartilhado["codigo_acesso"]},
        headers=headers_b,
    )
    assert entrar.status_code == 200

    criada = _criar_movimentacao(client, espaco_compartilhado["id"], headers_a)

    resposta = client.put(
        f"/espacos/{espaco_compartilhado['id']}/movimentacoes/{criada['id']}",
        json={
            "tipo": "GANHO",
            "categoria": "Teste",
            "descricao": "Tentativa indevida",
            "valor": 123.45,
            "data": "2026-08-05",
        },
        headers=headers_b,
    )

    assert resposta.status_code == 403


def test_impede_edicao_em_espaco_sem_permissao(client):
    (_, headers_a), (_, headers_b) = (
        cadastrar(client, "Ana", "ana_sem_permissao@example.com"),
        cadastrar(client, "Bruno", "bruno_sem_permissao@example.com"),
    )

    espaco_a = _espaco_pessoal(client, headers_a)
    criada = _criar_movimentacao(client, espaco_a["id"], headers_a)

    resposta = client.put(
        f"/espacos/{espaco_a['id']}/movimentacoes/{criada['id']}",
        json={
            "tipo": "GANHO",
            "categoria": "Teste",
            "descricao": "Sem permissao",
            "valor": 10,
            "data": "2026-08-05",
        },
        headers=headers_b,
    )

    assert resposta.status_code == 403


def test_rollback_em_falha_de_commit_na_edicao_nao_remove_dados(client, db, monkeypatch):
    cadastro, headers = cadastrar(client, "Ana", "ana_rollback@example.com")
    usuario_id = cadastro["usuario"]["id"]
    espaco = _espaco_pessoal(client, headers)
    criada = _criar_movimentacao(client, espaco["id"], headers, descricao="Descricao original")

    rollback_chamado = {"ok": False}
    original_commit = db.commit
    original_rollback = db.rollback

    def commit_com_falha():
        raise SQLAlchemyError("falha forçada")

    def rollback_monitorado():
        rollback_chamado["ok"] = True
        return original_rollback()

    monkeypatch.setattr(db, "commit", commit_com_falha)
    monkeypatch.setattr(db, "rollback", rollback_monitorado)

    resposta = client.put(
        f"/espacos/{espaco['id']}/movimentacoes/{criada['id']}",
        json={
            "tipo": "GANHO",
            "categoria": "Teste",
            "descricao": "Nao deveria persistir",
            "valor": 999,
            "data": "2026-08-05",
        },
        headers=headers,
    )

    monkeypatch.setattr(db, "commit", original_commit)
    monkeypatch.setattr(db, "rollback", original_rollback)

    assert resposta.status_code == 500
    assert rollback_chamado["ok"] is True

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    assert usuario is not None

    espaco_db = db.query(EspacoFinanceiro).filter(EspacoFinanceiro.id == espaco["id"]).first()
    assert espaco_db is not None

    mov_db = db.query(Movimentacao).filter(Movimentacao.id == criada["id"]).first()
    assert mov_db is not None
    assert mov_db.descricao == "Descricao original"


def test_fluxo_e2e_cadastro_login_criacao_edicao_logout_relogin(client):
    cadastro, headers = cadastrar(client, "Ana", "ana_e2e@example.com")
    espaco = _espaco_pessoal(client, headers)
    criada = _criar_movimentacao(client, espaco["id"], headers)

    edicao = client.put(
        f"/espacos/{espaco['id']}/movimentacoes/{criada['id']}",
        json={
            "tipo": "GANHO",
            "categoria": "Teste",
            "descricao": "Preservada apos relogin",
            "valor": 200,
            "data": "2026-08-05",
        },
        headers=headers,
    )
    assert edicao.status_code == 200

    dashboard = client.get(f"/espacos/{espaco['id']}/dashboard/resumo", headers=headers)
    assert dashboard.status_code == 200

    logout = client.post("/auth/logout", headers=headers)
    assert logout.status_code == 204

    relogin = client.post("/auth/login", json={"email": "ana_e2e@example.com", "senha": "senha123"})
    assert relogin.status_code == 200
    novo_headers = {"Authorization": f"Bearer {relogin.json()['access_token']}"}

    lista = client.get(f"/espacos/{espaco['id']}/movimentacoes/", headers=novo_headers)
    assert lista.status_code == 200
    assert any(item["descricao"] == "Preservada apos relogin" for item in lista.json())


def test_isolamento_duas_contas_na_edicao(client):
    (_, headers_a), (_, headers_b) = (
        cadastrar(client, "Ana", "ana_isolamento@example.com"),
        cadastrar(client, "Bruno", "bruno_isolamento@example.com"),
    )

    espaco_a = _espaco_pessoal(client, headers_a)
    mov_a = _criar_movimentacao(client, espaco_a["id"], headers_a, descricao="Somente Ana")

    resposta_b = client.put(
        f"/espacos/{espaco_a['id']}/movimentacoes/{mov_a['id']}",
        json={
            "tipo": "GANHO",
            "categoria": "Teste",
            "descricao": "Tentativa Bruno",
            "valor": 1,
            "data": "2026-08-05",
        },
        headers=headers_b,
    )
    assert resposta_b.status_code == 403

    lista_a = client.get(f"/espacos/{espaco_a['id']}/movimentacoes/", headers=headers_a)
    assert lista_a.status_code == 200
    assert any(item["descricao"] == "Somente Ana" for item in lista_a.json())
