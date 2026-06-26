from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.movimentacao_schemas import (
    CriarMovimentacao,
    AtualizarMovimentacao
)
from app.services.movimentacao_service import (
    criar_movimentacao,
    listar_movimentacoes,
    atualizar_movimentacao,
    deletar_movimentacao,
)

router = APIRouter(prefix="/movimentacoes", tags=["Movimentações"])


@router.post(
    "/",
    summary="Cadastra uma nova movimentação",
    description="Rota para cadastrar uma nova movimentação no banco de dados"
)
def criar(dado: CriarMovimentacao, db: Session = Depends(get_db)):
    return criar_movimentacao(db, dado)


@router.get(
    "/",
    summary="Visualizar movimentações",
    description="Retorna todas as movimentações cadastradas no banco de dados"
)
def view(db: Session = Depends(get_db)):
    return listar_movimentacoes(db)


@router.put(
    "/{id}",
    summary="Atualizar movimentação",
    description="Atualiza uma movimentação cadastrada no banco de dados"
)
def update(id: int, dado: AtualizarMovimentacao, db: Session = Depends(get_db)):
    return atualizar_movimentacao(db, id, dado)


@router.delete(
    "/{id}",
    summary="Deletar movimentação",
    description="Deleta uma movimentação cadastrada no banco de dados"
)
def delete(id: int, db: Session = Depends(get_db)):
    return deletar_movimentacao(db, id)


