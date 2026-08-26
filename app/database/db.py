import logging
import time

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.request_context import request_metrics_var

settings = get_settings()
logger = logging.getLogger(__name__)

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


@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(_conn, _cursor, statement, _parameters, context, _executemany):
    context._autogestor_query_started_at = time.perf_counter()
    metrics = request_metrics_var.get({})
    metrics["sql_count"] = int(metrics.get("sql_count", 0)) + 1
    if "sql_first_query_ms" not in metrics:
        metrics["sql_first_query_ms"] = 0.0
    request_metrics_var.set(metrics)


@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(_conn, _cursor, statement, _parameters, context, _executemany):
    started = getattr(context, "_autogestor_query_started_at", None)
    elapsed_ms = 0.0
    if started is not None:
        elapsed_ms = (time.perf_counter() - started) * 1000

    metrics = request_metrics_var.get({})
    metrics["sql_total_ms"] = float(metrics.get("sql_total_ms", 0.0)) + elapsed_ms
    if "sql_first_query_ms" in metrics and not metrics.get("sql_first_query_seen"):
        metrics["sql_first_query_ms"] = elapsed_ms
        metrics["sql_first_query_seen"] = 1
    request_metrics_var.set(metrics)

    if settings.enable_server_timing:
        logger.debug(
            "sql_query request_id=%s duration_ms=%.2f statement=%s",
            metrics.get("request_id", "n/a"),
            elapsed_ms,
            statement.split("\n", 1)[0][:120],
        )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
