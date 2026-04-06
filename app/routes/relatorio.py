from app.database.db import lista_ganhos, lista_gastos
from fastapi import APIRouter

router = APIRouter(prefix='/relatorio', tags=['Relatório'])

@router.get('/',
    summary='Dashboard',
    description='Nessa rota será possível vizualizar um dashboard'
)
def relatorio():
    total_gastos = sum(gastos['valor'] for gastos in lista_gastos)
    total_ganhos = sum(ganhos['valor'] for ganhos in lista_ganhos)

    return {
        'Ganhos': total_ganhos,
        'Gastos': total_gastos,
        'Lucro': total_ganhos - total_gastos
    }

@router.get('/por-tipo',
    summary='Separa os gastos por categoria',
    description='Busca no banco de dados os gatos separados por categoria. '        
)
def gastos_por_tipo():
    resultado = {}

    for g in lista_gastos:
        tipo = g['tipo']
        resultado.setdefault(tipo, 0)
        resultado[tipo] += g['valor']

    return resultado

