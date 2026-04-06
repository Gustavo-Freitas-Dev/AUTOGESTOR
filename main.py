from fastapi import FastAPI
from app.routes.ganhos import router as rota_ganhos
from app.routes.gastos import router as rota_gastos
from app.routes.relatorio import router as rota_relatorios

app = FastAPI()

app.include_router(rota_ganhos)
app.include_router(rota_gastos)
app.include_router(rota_relatorios)

@app.get(
    '/',
    tags=['Sistema'],
    summary='Verifica se a API está online',
    description='Rota inicial para testar se a API está funcionando corretamente'
)
def home():
    return {'message': 'A API está no ar.'}