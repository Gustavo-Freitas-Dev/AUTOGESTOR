from fastapi import APIRouter
from app.schemas.gastos_schemas import CriarGastos
from app.database.db import lista_gastos, contador_gastos

router = APIRouter(prefix='/ganhos', tags=['Gastos'])

@router.post('/gastos',
    summary='Cadastra um novo gasto',
    description='Rota para cadastrar um novo gasto ao banco de dados'
)
def add_gastos(dado_gasto: CriarGastos):
    global contador_gastos

    gasto = {
        'id': contador_gastos,
        'tipo': dado_gasto.tipo.upper(),
        'valor': dado_gasto.valor 
    }

    lista_gastos.append(gasto)
    contador_gastos += 1

    return gasto

@router.get('/gastos',
    summary='Vizualizar os gastos',
    description='Retorna todos os gatos cadastrados no banco de dados'
)
def view_gastos():
    return lista_gastos