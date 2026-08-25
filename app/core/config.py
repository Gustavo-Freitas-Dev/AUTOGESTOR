import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="AutoGestor API", alias="AUTOGESTOR_APP_NAME")
    app_description: str = Field(
        default="API para controle financeiro com autenticacao e espacos colaborativos.",
        alias="AUTOGESTOR_APP_DESCRIPTION",
    )
    app_version: str = Field(default="1.0.0", alias="AUTOGESTOR_APP_VERSION")
    app_env: str = Field(default="development", alias="AUTOGESTOR_APP_ENV")

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    allow_sqlite_fallback: bool = Field(default=True, alias="AUTOGESTOR_ALLOW_SQLITE_FALLBACK")
    db_connect_timeout_seconds: int = Field(default=5, alias="AUTOGESTOR_DB_CONNECT_TIMEOUT_SECONDS")
    db_statement_timeout_ms: int = Field(default=12000, alias="AUTOGESTOR_DB_STATEMENT_TIMEOUT_MS")
    enable_server_timing: bool = Field(default=False, alias="AUTOGESTOR_ENABLE_SERVER_TIMING")

    jwt_secret_key: str = Field(default="changeme-dev-secret", alias="AUTOGESTOR_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=10080, alias="AUTOGESTOR_ACCESS_TOKEN_EXPIRE_MINUTES")

    password_reset_token_expire_minutes: int = Field(
        default=30,
        alias="AUTOGESTOR_PASSWORD_RESET_TOKEN_EXPIRE_MINUTES",
    )
    password_reset_uniform_delay_ms: int = Field(
        default=200,
        alias="AUTOGESTOR_PASSWORD_RESET_UNIFORM_DELAY_MS",
    )
    password_reset_request_limit_per_ip: int = Field(
        default=10,
        alias="AUTOGESTOR_PASSWORD_RESET_REQUEST_LIMIT_PER_IP",
    )
    password_reset_request_limit_per_email: int = Field(
        default=5,
        alias="AUTOGESTOR_PASSWORD_RESET_REQUEST_LIMIT_PER_EMAIL",
    )
    password_reset_confirm_limit_per_ip: int = Field(
        default=20,
        alias="AUTOGESTOR_PASSWORD_RESET_CONFIRM_LIMIT_PER_IP",
    )
    password_reset_rate_limit_window_seconds: int = Field(
        default=900,
        alias="AUTOGESTOR_PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS",
    )

    app_base_url: str = Field(default="http://127.0.0.1:8000", alias="AUTOGESTOR_APP_BASE_URL")
    email_provider: str = Field(default="log", alias="AUTOGESTOR_EMAIL_PROVIDER")
    email_from: str = Field(default="AutoGestor <nao-responda@example.com>", alias="AUTOGESTOR_EMAIL_FROM")
    email_smtp_host: str | None = Field(default=None, alias="AUTOGESTOR_EMAIL_SMTP_HOST")
    email_smtp_port: int = Field(default=587, alias="AUTOGESTOR_EMAIL_SMTP_PORT")
    email_smtp_username: str | None = Field(default=None, alias="AUTOGESTOR_EMAIL_SMTP_USERNAME")
    email_smtp_password: str | None = Field(default=None, alias="AUTOGESTOR_EMAIL_SMTP_PASSWORD")
    email_smtp_use_tls: bool = Field(default=True, alias="AUTOGESTOR_EMAIL_SMTP_USE_TLS")

    cors_origins: str = Field(default="http://127.0.0.1:8000,http://localhost:8000", alias="AUTOGESTOR_CORS_ORIGINS")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"} or bool(os.getenv("VERCEL"))

    @staticmethod
    def _normalize_database_url(url: str) -> str:
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def effective_database_url(self) -> str:
        raw_url = self.database_url
        if raw_url:
            normalized = self._normalize_database_url(raw_url)
            if self.is_production and normalized.startswith("sqlite"):
                raise RuntimeError(
                    "DATABASE_URL em producao/Vercel deve apontar para PostgreSQL, nao SQLite."
                )
            return normalized

        if self.is_production:
            raise RuntimeError(
                "DATABASE_URL obrigatoria em producao/Vercel. Configure um PostgreSQL externo."
            )

        if self.allow_sqlite_fallback:
            return "sqlite:///autogestor.db"

        raise RuntimeError(
            "DATABASE_URL nao configurada e fallback SQLite desativado."
        )

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [item.strip() for item in self.cors_origins.split(",")]
        return [origin for origin in origins if origin]

    @property
    def effective_jwt_secret_key(self) -> str:
        secret = (self.jwt_secret_key or "").strip()
        if self.is_production and (not secret or secret == "changeme-dev-secret"):
            raise RuntimeError(
                "AUTOGESTOR_SECRET_KEY obrigatoria em producao/Vercel e nao pode usar valor padrao."
            )
        return secret or "changeme-dev-secret"

    @property
    def normalized_app_base_url(self) -> str:
        return self.app_base_url.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
