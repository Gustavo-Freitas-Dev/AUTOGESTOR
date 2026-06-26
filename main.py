from fastapi import FastAPI
from app.routes.movimentacoes import router as movimentacoes_router
from fastapi.staticfiles import StaticFiles
from app.database.db import engine
from app.database.base import Base


Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(movimentacoes_router)

@app.get(
    '/',
    tags=['Sistema'],
    summary='Verifica se a API está online',
    description='Rota inicial para testar se a API está funcionando corretamente'
)
def home():
    return {'message': 'A API está no ar 🚀'}