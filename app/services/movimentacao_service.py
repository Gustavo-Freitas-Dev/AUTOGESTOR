from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.movimentacao import Movimentacao
from app.schemas.movimentacao_schemas import (
    CriarMovimentacao,
    AtualizarMovimentacao
)


def criar_movimentacao(db: Session, dado: CriarMovimentacao):

    movimentacao = Movimentacao(
        tipo=dado.tipo,
        categoria=dado.categoria,
        descricao=dado.descricao,
        valor=dado.valor,
        data=dado.data
    )

    db.add(movimentacao)
    db.commit()
    db.refresh(movimentacao)

    return movimentacao


def listar_movimentacoes(db: Session):
    return db.query(Movimentacao).all()


def atualizar_movimentacao(db: Session, id: int, dado: AtualizarMovimentacao):

    movimentacao = db.query(Movimentacao).filter(Movimentacao.id == id).first()

    if not movimentacao:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")

    movimentacao.tipo = dado.tipo
    movimentacao.categoria = dado.categoria
    movimentacao.descricao = dado.descricao
    movimentacao.valor = dado.valor
    movimentacao.data = dado.data

    db.commit()
    db.refresh(movimentacao)

    return {
        "message": "Movimentação atualizada com sucesso",
        "movimentacao": movimentacao
    }


def deletar_movimentacao(db: Session, id: int):

    movimentacao = db.query(Movimentacao).filter(Movimentacao.id == id).first()

    if not movimentacao:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")

    db.delete(movimentacao)
    db.commit()

    return {
        "message": "Movimentação deletada com sucesso"
    }