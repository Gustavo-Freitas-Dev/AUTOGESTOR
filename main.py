from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.database.base import Base
from app.database.db import engine

# ESTA LINHA É A QUE FALTAVA:
from app.models.espaco_financeiro import EspacoFinanceiro  # noqa: F401
from app.models.membro_espaco import MembroEspaco  # noqa: F401
from app.models.movimentacao import Movimentacao  # noqa: F401
from app.models.usuario_model import Usuario  # noqa: F401
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.espacos import router as espacos_router
from app.routes.movimentacoes import router as movimentacoes_router

settings = get_settings()


@asynccontextmanager
async def app_lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
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
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "environment": settings.app_env}

@app.get('/', tags=['Sistema'], summary='Verifica se a API está online')
def home() -> dict[str, str]:
    return {'message': 'A API esta no ar'}


@app.get('/docs/', include_in_schema=False)
def docs_redirect() -> RedirectResponse:
    return RedirectResponse(url='/docs')
