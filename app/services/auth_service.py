"""
app/services/auth_service.py
───────────────────────────────
Lógica de autenticação: hash de senha, geração e validação de JWT.

DEPENDÊNCIAS NOVAS que você precisa instalar:
    uv add passlib[bcrypt] python-jose[cryptography]

  passlib[bcrypt]        → hash seguro de senha (nunca guardamos senha em texto puro)
  python-jose[cryptography] → criação e validação de tokens JWT
"""

import logging
from datetime import UTC, datetime, timedelta

from email_validator import EmailNotValidError, validate_email
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.usuario_model import Usuario

settings = get_settings()
SECRET_KEY = settings.effective_jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expire_minutes
logger = logging.getLogger(__name__)


class AuthServiceUnavailableError(Exception):
    pass


def mascarar_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    local_mask = (local[:2] + "***") if local else "***"
    domain_mask = (domain[:2] + "***") if domain else "***"
    return f"{local_mask}@{domain_mask}"


def normalizar_email(email: str) -> str:
    candidato = str(email or "").strip().lower()
    try:
        validado = validate_email(candidato, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValueError("E-mail invalido.") from exc
    return validado.email

# Contexto do passlib configurado para usar bcrypt — algoritmo
# de hash padrão da indústria para senhas (lento de propósito,
# o que dificulta ataques de força bruta).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    """Gera o hash bcrypt de uma senha em texto puro."""
    return pwd_context.hash(senha)


def validar_requisitos_senha(senha: str) -> tuple[bool, str | None]:
    if not senha or len(senha) < 6:
        return False, "A senha precisa ter pelo menos os requisitos informados."
    return True, None


def verificar_senha(senha_texto: str, senha_hash: str) -> bool:
    """
    Compara a senha digitada no login com o hash salvo no banco.
    Retorna True se baterem, False caso contrário.
    Nunca comparamos string com string diretamente — o bcrypt
    cuida da comparação de forma segura (constant-time).
    """
    return pwd_context.verify(senha_texto, senha_hash)


def criar_access_token(dados: dict) -> str:
    """
    Gera um JWT assinado contendo os dados passados (geralmente
    {"sub": email_do_usuario}) mais a data de expiração.

    "sub" (subject) é o nome de campo padrão do JWT para identificar
    o dono do token.
    """
    to_encode = dados.copy()
    expira_em = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    if "tv" not in to_encode:
        to_encode["tv"] = 0
    to_encode.update({"exp": expira_em})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> int | None:
    """
    Valida o token e retorna o email do usuário (campo "sub") se
    o token for válido. Retorna None se o token for inválido,
    expirado ou adulterado.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        return int(subject) if subject is not None else None
    except (JWTError, TypeError, ValueError):
        return None


def validar_token(token: str) -> tuple[int | None, int | None, str | None]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        token_version = payload.get("tv", 0)
        if subject is None:
            return None, None, "token_invalid"
        return int(subject), int(token_version), None
    except ExpiredSignatureError:
        return None, None, "token_expired"
    except (JWTError, TypeError, ValueError):
        return None, None, "token_invalid"


def buscar_usuario_por_email(db: Session, email: str) -> Usuario | None:
    email_normalizado = normalizar_email(email)
    return db.query(Usuario).filter(func.lower(Usuario.email) == email_normalizado).first()


def buscar_usuario_por_id(db: Session, usuario_id: int) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.id == usuario_id).first()


def autenticar_usuario(db: Session, email: str, senha: str) -> Usuario | None:
    """
    Fluxo completo de login: busca o usuário pelo email e confere
    a senha. Retorna o usuário se tudo bater, None caso contrário.

    Note que retornamos None tanto para "email não existe" quanto
    para "senha errada" — isso é proposital. Se a API respondesse
    mensagens diferentes para cada caso ("email não encontrado" vs
    "senha incorreta"), um atacante poderia descobrir quais emails
    estão cadastrados no sistema testando um por um. Por segurança,
    a mensagem de erro do login deve ser sempre genérica
    ("email ou senha incorretos").
    """
    try:
        usuario = buscar_usuario_por_email(db, email)
    except SQLAlchemyError as exc:
        logger.exception("Falha de banco ao buscar usuario no login")
        raise AuthServiceUnavailableError("database_unavailable") from exc

    if not usuario:
        logger.info("Login sem usuario correspondente", extra={"email_mask": mascarar_email(email)})
        return None

    try:
        senha_ok = verificar_senha(senha, usuario.senha_hash)
    except Exception as exc:
        logger.exception("Falha na verificacao de hash de senha")
        raise AuthServiceUnavailableError("password_verification_failed") from exc

    if not senha_ok:
        logger.info("Login com senha invalida", extra={"user_id": usuario.id})
        return None

    logger.info("Login autenticado com sucesso", extra={"user_id": usuario.id})
    return usuario
