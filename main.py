import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.request_context import request_metrics_var
from app.database.db import engine
from app.database.dependencies import get_db
from app.models.espaco_financeiro import EspacoFinanceiro  # noqa: F401
from app.models.membro_espaco import MembroEspaco  # noqa: F401
from app.models.movimentacao import Movimentacao  # noqa: F401
from app.models.password_reset_token import PasswordResetToken  # noqa: F401
from app.models.usuario_model import Usuario  # noqa: F401
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.espacos import router as espacos_router
from app.routes.movimentacoes import router as movimentacoes_router

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Database dialect: %s", engine.dialect.name)
    yield


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    openapi_tags=[
        {"name": "Sistema", "description": "Saúde e metadados da aplicação."},
        {"name": "Autenticação", "description": "Cadastro, login e perfil do usuário."},
        {"name": "Espaços financeiros", "description": "Gestão de espaços pessoais e compartilhados."},
        {"name": "Movimentações", "description": "CRUD de ganhos e gastos por espaço."},
        {"name": "Dashboard", "description": "Indicadores e consultas analíticas por espaço."},
    ],
    lifespan=app_lifespan,
)
app.state.enable_server_timing = settings.enable_server_timing


@app.middleware("http")
async def request_timing_middleware(request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    metrics_token = request_metrics_var.set({"request_id": request_id})

    started = time.perf_counter()
    response = None
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        total_ms = (time.perf_counter() - started) * 1000
        metrics = request_metrics_var.get({})
        logger.info(
            "request request_id=%s method=%s path=%s status_code=%s duration_ms=%.2f sql_count=%s sql_total_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            status_code,
            total_ms,
            metrics.get("sql_count", 0),
            float(metrics.get("sql_total_ms", 0.0)),
        )

        if response is not None:
            response.headers["X-Request-ID"] = request_id
            if app.state.enable_server_timing:
                existing = response.headers.get("Server-Timing")
                total_metric = f"app_total;dur={total_ms:.2f}"
                response.headers["Server-Timing"] = f"{existing}, {total_metric}" if existing else total_metric

        request_metrics_var.reset(metrics_token)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path("app/static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(movimentacoes_router)
app.include_router(dashboard_router)
app.include_router(auth_router)
app.include_router(espacos_router)


@app.get("/health", tags=["Sistema"], summary="Health check da aplicação")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/health/database", tags=["Sistema"], summary="Health check do banco de dados")
def health_database(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database_unavailable") from exc
    return {"status": "ok", "database": "reachable"}


@app.get("/", include_in_schema=False)
def home() -> RedirectResponse:
    return RedirectResponse(url="/static/login.html", status_code=307)


@app.get("/docs/", include_in_schema=False)
def docs_redirect() -> RedirectResponse:
    return RedirectResponse(url="/docs")
