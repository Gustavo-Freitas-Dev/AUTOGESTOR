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

    database_url: str = Field(default="sqlite:///autogestor.db", alias="DATABASE_URL")
    autogestor_database_url: str | None = Field(default=None, alias="AUTOGESTOR_DATABASE_URL")

    jwt_secret_key: str = Field(default="changeme-dev-secret", alias="AUTOGESTOR_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=10080, alias="AUTOGESTOR_ACCESS_TOKEN_EXPIRE_MINUTES")

    cors_origins: str = Field(default="http://127.0.0.1:8000,http://localhost:8000", alias="AUTOGESTOR_CORS_ORIGINS")

    @property
    def effective_database_url(self) -> str:
        return self.autogestor_database_url or self.database_url

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [item.strip() for item in self.cors_origins.split(",")]
        return [origin for origin in origins if origin]


@lru_cache
def get_settings() -> Settings:
    return Settings()
