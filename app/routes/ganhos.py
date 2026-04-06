from fastapi import APIRouter
from app.schemas.ganhos_schemas import CriarGanho, AtualizarGanho
from app.database.db import lista_ganhos, contador_ganhos

router = APIRouter(prefix='/ganhos', tags=['Ganhos'])

@router.post(
    '/adicionar',
    summary='Cadastra um novo ganho',
    description='Rota para cadastrar um novo ganho ao banco de dados'
)
def add_ganho(dado_ganho: CriarGanho):
    global contador_ganhos

    ganho = {
        'id': contador_ganhos,
        'plataforma': dado_ganho.plataforma.upper(),
        'valor': dado_ganho.valor
    }

    lista_ganhos.append(ganho)
    contador_ganhos += 1

    return ganho

@router.get('/listar',
    summary='Listas todos os ganhos cadastrados',
    description='Essa rota retorna todos os ganhos do banco de dados'
)
def view_ganhos():
    return lista_ganhos

@router.put('/atualizar/{id}',
    summary='Atualizar um ganho',
    description='Essa rota atualiza um ganho cadastrado no banco de dados'
)
def atualizar(id: int, dado: AtualizarGanho):
    for ganho in lista_ganhos:
        if ganho['id'] == id:
            ganho['plataforma'] = dado.plataforma
            ganho['valor'] = dado.valor
            return ganho
    return {'ERRO': 'ID não encontrado'}
            
@router.delete(
    '/deletar/{id}',
    summary='Deletar ganho',
    description='Essa rota deleta um ganho cadastrado no banco de dados.'
)
def deletar(id:int):
    for ganho in lista_ganhos:
        if ganho['id'] == id:
            lista_ganhos.remove(ganho)
            return {'Deletado': ganho}
    return {'ERRO': 'ID não encontrado.'}