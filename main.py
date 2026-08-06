from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.movimentacoes import router as movimentacoes_router
from app.routes.dashboard import router as dashboard_router
from app.routes.auth import router as auth_router
from app.routes.espacos import router as espacos_router
from fastapi.staticfiles import StaticFiles
from app.database.db import engine
from app.database.base import Base

# ESTA LINHA É A QUE FALTAVA:
from app.models.usuario_model import Usuario
from app.models.movimentacao import Movimentacao
from app.models.espaco_financeiro import EspacoFinanceiro
from app.models.membro_espaco import MembroEspaco

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(movimentacoes_router)
app.include_router(dashboard_router)
app.include_router(auth_router)
app.include_router(espacos_router)

@app.get('/', tags=['Sistema'], summary='Verifica se a API está online')
def home():
    return {'message': 'A API está no ar 🚀'}
