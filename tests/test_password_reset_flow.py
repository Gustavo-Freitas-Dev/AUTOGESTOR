from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from conftest import cadastrar
from sqlalchemy.orm import sessionmaker

import app.routes.auth as auth_routes
from app.models.password_reset_token import PasswordResetToken
from app.services.password_reset_service import redefinir_senha_com_token
from app.services.rate_limit_service import rate_limiter


class FakeEmailService:
    def __init__(self):
        self.payloads = []

    def send_password_reset(self, payload):
        self.payloads.append(payload)


def _extrair_token_link(link: str) -> str:
    query = parse_qs(urlparse(link).query)
    return query.get("token", [""])[0]


def test_esqueci_senha_resposta_generica_para_email_existente_e_inexistente(client, monkeypatch):
    rate_limiter.reset()
    cadastrar(client, "Ana", "ana_reset@example.com")

    fake_email = FakeEmailService()
    monkeypatch.setattr(auth_routes, "get_email_service", lambda: fake_email)

    r1 = client.post("/auth/esqueci-senha", json={"email": "ana_reset@example.com"})
    r2 = client.post("/auth/esqueci-senha", json={"email": "naoexiste@example.com"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["message"] == r2.json()["message"]
    assert len(fake_email.payloads) == 1


def test_esqueci_senha_cria_apenas_hash_no_banco(client, db, monkeypatch):
    rate_limiter.reset()
    cadastrar(client, "Ana", "hash_token_reset@example.com")

    fake_email = FakeEmailService()
    monkeypatch.setattr(auth_routes, "get_email_service", lambda: fake_email)

    resposta = client.post("/auth/esqueci-senha", json={"email": "  HASH_TOKEN_RESET@EXAMPLE.COM "})
    assert resposta.status_code == 200
    assert len(fake_email.payloads) == 1

    token_link = _extrair_token_link(fake_email.payloads[0].reset_link)
    assert token_link

    registro = db.query(PasswordResetToken).first()
    assert registro is not None
    assert registro.token_hash != token_link
    assert len(registro.token_hash) == 64


def test_redefinir_senha_com_token_valido_invalida_jwt_antigo(client, monkeypatch):
    rate_limiter.reset()
    cadastro, _ = cadastrar(client, "Ana", "redefinir_ok@example.com")
    jwt_antigo = cadastro["access_token"]

    fake_email = FakeEmailService()
    monkeypatch.setattr(auth_routes, "get_email_service", lambda: fake_email)

    forgot = client.post("/auth/esqueci-senha", json={"email": "redefinir_ok@example.com"})
    assert forgot.status_code == 200

    token = _extrair_token_link(fake_email.payloads[0].reset_link)
    assert token

    redefinir = client.post(
        "/auth/redefinir-senha",
        json={"token": token, "nova_senha": "novaSenha123!", "confirmar_senha": "novaSenha123!"},
    )
    assert redefinir.status_code == 200

    login_antigo = client.post(
        "/auth/login",
        json={"email": "redefinir_ok@example.com", "senha": "senha123"},
    )
    assert login_antigo.status_code == 401

    login_novo = client.post(
        "/auth/login",
        json={"email": "redefinir_ok@example.com", "senha": "novaSenha123!"},
    )
    assert login_novo.status_code == 200

    me_com_jwt_antigo = client.get("/auth/me", headers={"Authorization": f"Bearer {jwt_antigo}"})
    assert me_com_jwt_antigo.status_code == 401
    assert me_com_jwt_antigo.json()["detail"] == "token_revoked"


def test_redefinir_senha_recusa_token_reutilizado(client, monkeypatch):
    rate_limiter.reset()
    cadastrar(client, "Ana", "reuse_reset@example.com")

    fake_email = FakeEmailService()
    monkeypatch.setattr(auth_routes, "get_email_service", lambda: fake_email)

    client.post("/auth/esqueci-senha", json={"email": "reuse_reset@example.com"})
    token = _extrair_token_link(fake_email.payloads[0].reset_link)

    primeira = client.post(
        "/auth/redefinir-senha",
        json={"token": token, "nova_senha": "novaSenha123!", "confirmar_senha": "novaSenha123!"},
    )
    segunda = client.post(
        "/auth/redefinir-senha",
        json={"token": token, "nova_senha": "outraSenha123!", "confirmar_senha": "outraSenha123!"},
    )

    assert primeira.status_code == 200
    assert segunda.status_code == 400
    assert segunda.json()["detail"] == "token_invalid"


def test_redefinir_senha_recusa_token_expirado(client, db, monkeypatch):
    rate_limiter.reset()
    cadastrar(client, "Ana", "expira_reset@example.com")

    fake_email = FakeEmailService()
    monkeypatch.setattr(auth_routes, "get_email_service", lambda: fake_email)

    client.post("/auth/esqueci-senha", json={"email": "expira_reset@example.com"})
    token = _extrair_token_link(fake_email.payloads[0].reset_link)

    registro = db.query(PasswordResetToken).first()
    registro.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    resposta = client.post(
        "/auth/redefinir-senha",
        json={"token": token, "nova_senha": "novaSenha123!", "confirmar_senha": "novaSenha123!"},
    )

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "token_expired"


def test_redefinir_senha_recusa_senhas_diferentes(client):
    rate_limiter.reset()
    resposta = client.post(
        "/auth/redefinir-senha",
        json={"token": "abc123tokenmuitogrande", "nova_senha": "abc12345", "confirmar_senha": "abc12346"},
    )
    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "As senhas não coincidem."


def test_rate_limit_em_esqueci_senha(client, monkeypatch):
    rate_limiter.reset()
    cadastrar(client, "Ana", "ratelimit_reset@example.com")

    limite_original = auth_routes.settings.password_reset_request_limit_per_email
    auth_routes.settings.password_reset_request_limit_per_email = 1
    try:
        primeira = client.post("/auth/esqueci-senha", json={"email": "ratelimit_reset@example.com"})
        segunda = client.post("/auth/esqueci-senha", json={"email": "ratelimit_reset@example.com"})
    finally:
        auth_routes.settings.password_reset_request_limit_per_email = limite_original

    assert primeira.status_code == 200
    assert segunda.status_code == 429


def test_login_html_tem_confirmacao_e_link_esqueci_senha():
    with open("app/static/login.html", encoding="utf-8") as f:
        html = f.read()

    assert "Confirmar senha" in html
    assert "cad-confirmar-senha" in html
    assert "Esqueci minha senha" in html
    assert "As senhas não coincidem." in html


def test_redefinir_html_tem_campos_e_higiene_de_token():
    with open("app/static/redefinir-senha.html", encoding="utf-8") as f:
        html = f.read()

    assert "history.replaceState" in html
    assert "nova_senha" in html
    assert "confirmar_senha" in html
    assert "Token inválido ou já utilizado" in html


def test_redefinicao_simultanea_consumo_unico_do_token(client, db, monkeypatch):
    rate_limiter.reset()
    cadastrar(client, "Ana", "concorrencia_reset@example.com")

    fake_email = FakeEmailService()
    monkeypatch.setattr(auth_routes, "get_email_service", lambda: fake_email)

    client.post("/auth/esqueci-senha", json={"email": "concorrencia_reset@example.com"})
    token = _extrair_token_link(fake_email.payloads[0].reset_link)

    SessionFactory = sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False)

    def tentativa(nova_senha: str):
        sessao = SessionFactory()
        try:
            return redefinir_senha_com_token(sessao, token, nova_senha)
        finally:
            sessao.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        r1 = pool.submit(tentativa, "novaSenhaAAA1!")
        r2 = pool.submit(tentativa, "novaSenhaBBB1!")
        resultado1 = r1.result()
        resultado2 = r2.result()

    resultados = [resultado1, resultado2]
    sucessos = [r for r in resultados if r[0] is True]
    falhas = [r for r in resultados if r[0] is False]

    assert len(sucessos) == 1
    assert len(falhas) == 1
    assert falhas[0][1] == "token_invalid"
