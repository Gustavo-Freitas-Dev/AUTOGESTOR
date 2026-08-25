from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

DATABASE_URL = settings.effective_database_url

engine_options: dict[str, object] = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    # Em ambiente serverless, NullPool evita conexoes ociosas presas entre invocacoes.
    engine_options["poolclass"] = NullPool
    engine_options["pool_recycle"] = 300
    engine_options["connect_args"] = {
        "connect_timeout": settings.db_connect_timeout_seconds,
    }

engine = create_engine(
    DATABASE_URL,
    **engine_options,
)

if not DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_statement_timeout(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        try:
            timeout_ms = int(settings.db_statement_timeout_ms)
            cursor.execute(f"SET statement_timeout = {timeout_ms}")
        finally:
            cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
