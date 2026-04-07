from fastapi import APIRouter
from app.schemas.gastos_schemas import CriarGastos, AtualizarGastos
from app.database.db import lista_gastos, contador_gastos

router = APIRouter(prefix='/gastos', tags=['Gastos'])

@router.post('/',
    summary='Cadastra um novo gasto',
    description='Rota para cadastrar um novo gasto ao banco de dados'
)
def add_gastos(dado_gasto: CriarGastos):
    global contador_gastos

    gasto = {
        'id': contador_gastos,
        'categoria': dado_gasto.categoria.value,
        'descricao': dado_gasto.descricao.title(),
        'valor': dado_gasto.valor 
    }

    lista_gastos.append(gasto)
    contador_gastos += 1

    return gasto

@router.get('/',
    summary='Vizualizar os gastos',
    description='Retorna todos os gatos cadastrados no banco de dados'
)
def view_gastos():
    return lista_gastos

@router.put('/{id}',
    summary='Atualizar gastos',
    description='Rota para atualizar um gasto cadastrado no banco de dados.'
)
def update_gastos(id:int, dado:AtualizarGastos):
    for gasto in lista_gastos:
        if gasto['id'] == id:
            gasto['categoria'] = dado.categoria
            gasto['descricao'] = dado.descricao
            gasto['valor'] = dado.valor
            return {'ATUALIZADO': 'Gasto atualizado com sucesso!'}
    return {'ERRO': 'ID não indentificado.'}

@router.delete('/{id}',
    summary='Deleta um gasto',
    description='Rota para deletar um gasto cadastrado no banco de dados.'
)
def delete_gasto(id:int):
    for gasto in lista_gastos:
        if gasto['id'] == id:
            lista_gastos.remove(gasto)
            return {'DELETADO': gasto}
    return {'ERRO': 'ID não indentificado.'}