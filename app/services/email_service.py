import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class PasswordResetEmailPayload:
    to_email: str
    recipient_name: str
    reset_link: str
    expires_minutes: int
    request_id: str


class EmailService:
    def send_password_reset(self, payload: PasswordResetEmailPayload) -> None:
        raise NotImplementedError


class LogEmailService(EmailService):
    def send_password_reset(self, payload: PasswordResetEmailPayload) -> None:
        logger.info(
            "password_reset_email_enqueued request_id=%s recipient_domain=%s expires_minutes=%d",
            payload.request_id,
            payload.to_email.split("@")[-1] if "@" in payload.to_email else "unknown",
            payload.expires_minutes,
        )


class SmtpEmailService(EmailService):
    def __init__(self) -> None:
        self.settings = get_settings()

    def send_password_reset(self, payload: PasswordResetEmailPayload) -> None:
        if not self.settings.email_smtp_host:
            raise RuntimeError("AUTOGESTOR_EMAIL_SMTP_HOST nao configurado")

        subject = "AutoGestor - Redefinicao de senha"
        plain_text = (
            "Recebemos uma solicitacao para redefinir sua senha no AutoGestor.\n\n"
            f"Use o link abaixo para criar uma nova senha (expira em {payload.expires_minutes} minutos):\n"
            f"{payload.reset_link}\n\n"
            "Se voce nao solicitou a redefinicao, ignore este e-mail."
        )
        html = (
            "<p>Recebemos uma solicitacao para redefinir sua senha no <strong>AutoGestor</strong>.</p>"
            f"<p><a href=\"{payload.reset_link}\">Redefinir senha</a> (expira em {payload.expires_minutes} minutos).</p>"
            "<p>Se voce nao solicitou a redefinicao, ignore este e-mail.</p>"
        )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.settings.email_from
        message["To"] = payload.to_email
        message.set_content(plain_text)
        message.add_alternative(html, subtype="html")

        with smtplib.SMTP(self.settings.email_smtp_host, self.settings.email_smtp_port, timeout=10) as smtp:
            if self.settings.email_smtp_use_tls:
                smtp.starttls()
            if self.settings.email_smtp_username and self.settings.email_smtp_password:
                smtp.login(self.settings.email_smtp_username, self.settings.email_smtp_password)
            smtp.send_message(message)

        logger.info(
            "password_reset_email_sent request_id=%s recipient_domain=%s",
            payload.request_id,
            payload.to_email.split("@")[-1] if "@" in payload.to_email else "unknown",
        )


@lru_cache
def get_email_service() -> EmailService:
    settings = get_settings()
    provider = settings.email_provider.strip().lower()
    if provider == "smtp":
        return SmtpEmailService()
    return LogEmailService()
