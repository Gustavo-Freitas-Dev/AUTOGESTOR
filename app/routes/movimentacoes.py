from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.database.auth_dependencies import obter_usuario_atual
from app.services.espaco_service import verificar_acesso_espaco
from app.models.usuario_model import Usuario                      # ← novo import (tipo do usuário)
from app.schemas.movimentacao_schemas import (
    CriarMovimentacao,
    AtualizarMovimentacao
)
from app.services.movimentacao_service import (
    service_criar_movimentacao,
    service_listar_movimentacoes,
    service_atualizar_movimentacao,
    service_deletar_movimentacao,
    service_buscar_id,
)

router = APIRouter(prefix="/espacos/{espaco_id}/movimentacoes", tags=["Movimentações"])


@router.post(
    "/",
    summary="Cadastra uma nova movimentação",
    description="Rota para cadastrar uma nova movimentação no banco de dados, vinculada ao usuário logado"
)
def criar(
    espaco_id: int,
    dado: CriarMovimentacao,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),   # ← exige login
):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_criar_movimentacao(db, dado, usuario.id, espaco_id)


@router.get(
    "/",
    summary="Visualizar movimentações",
    description="Retorna apenas as movimentações do usuário logado"
)
def view(
    espaco_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),   # ← exige login
):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_listar_movimentacoes(db, espaco_id)


@router.put(
    "/{id}",
    summary="Atualizar movimentação",
    description="Atualiza uma movimentação, desde que pertença ao usuário logado"
)
def update(
    espaco_id: int,
    id: int,
    dado: AtualizarMovimentacao,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),   # ← exige login
):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_atualizar_movimentacao(db, id, dado, espaco_id)


@router.delete(
    "/{id}",
    summary="Deletar movimentação",
    description="Deleta uma movimentação, desde que pertença ao usuário logado"
)
def delete(
    espaco_id: int,
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),   # ← exige login
):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_deletar_movimentacao(db, id, espaco_id)


@router.get(
    "/{id}",
    summary='Busca movimentação pelo ID',
    description='Busca a movimentação pelo ID, desde que pertença ao usuário logado'
)
def buscar_id(
    espaco_id: int,
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),   # ← exige login
):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_buscar_id(db, id, espaco_id)
