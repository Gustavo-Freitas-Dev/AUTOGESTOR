import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.password_reset_token import PasswordResetToken
from app.models.usuario_model import Usuario
from app.services.auth_service import hash_senha, normalizar_email

logger = logging.getLogger(__name__)
settings = get_settings()


def gerar_token_recuperacao() -> str:
    return secrets.token_urlsafe(32)


def hash_token_recuperacao(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def mensagem_generica_recuperacao() -> str:
    return "Se existir uma conta com este e-mail, enviaremos as instrucoes para redefinir sua senha."


def criar_token_recuperacao(db: Session, usuario: Usuario) -> str:
    agora = datetime.now(UTC)
    expires_at = agora + timedelta(minutes=settings.password_reset_token_expire_minutes)
    token_texto = gerar_token_recuperacao()
    token_hash = hash_token_recuperacao(token_texto)

    db.query(PasswordResetToken).filter(
        PasswordResetToken.usuario_id == usuario.id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.revoked_at.is_(None),
    ).update({"revoked_at": agora}, synchronize_session=False)

    novo = PasswordResetToken(
        usuario_id=usuario.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(novo)
    return token_texto


def montar_link_recuperacao(token: str) -> str:
    return f"{settings.normalized_app_base_url}/static/redefinir-senha.html?token={token}"


def localizar_usuario_por_email(db: Session, email: str) -> Usuario | None:
    email_normalizado = normalizar_email(email)
    return db.query(Usuario).filter(Usuario.email == email_normalizado).first()


def redefinir_senha_com_token(db: Session, token: str, nova_senha: str) -> tuple[bool, str]:
    agora = datetime.now(UTC)
    token_hash = hash_token_recuperacao(token)

    try:
        stmt = (
            select(PasswordResetToken)
            .where(PasswordResetToken.token_hash == token_hash)
            .with_for_update()
        )
        registro = db.execute(stmt).scalar_one_or_none()
        if not registro:
            return False, "token_invalid"
        if registro.used_at is not None or registro.revoked_at is not None:
            return False, "token_invalid"
        expires_at = registro.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= agora:
            return False, "token_expired"

        atualizado = db.query(PasswordResetToken).filter(
            PasswordResetToken.id == registro.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.revoked_at.is_(None),
        ).update({"used_at": agora}, synchronize_session=False)
        if atualizado != 1:
            db.rollback()
            return False, "token_invalid"

        usuario = db.query(Usuario).filter(Usuario.id == registro.usuario_id).with_for_update().first()
        if not usuario:
            return False, "token_invalid"

        usuario.senha_hash = hash_senha(nova_senha)
        usuario.token_version = int(usuario.token_version or 0) + 1
        db.query(PasswordResetToken).filter(
            PasswordResetToken.usuario_id == usuario.id,
            PasswordResetToken.id != registro.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.revoked_at.is_(None),
        ).update({"revoked_at": agora}, synchronize_session=False)

        db.commit()
        return True, "password_reset_success"
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("password_reset_db_error")
        raise exc
