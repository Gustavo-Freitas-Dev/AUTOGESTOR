from datetime import date
from sqlalchemy.orm import Session
from app.models.movimentacao import Movimentacao
from sqlalchemy import func
from fastapi import HTTPException



def saldo_total(db: Session, espaco_id: int):

    ganhos = db.query(func.sum(Movimentacao.valor)).filter(Movimentacao.tipo == "GANHO", Movimentacao.espaco_id == espaco_id).scalar() or 0
    gastos = db.query(func.sum(Movimentacao.valor)).filter(Movimentacao.tipo == "GASTO", Movimentacao.espaco_id == espaco_id).scalar() or 0
    
    return {"Saldo": ganhos - gastos}         

def total_ganhos(db: Session, espaco_id: int):

    total = db.query(func.sum(Movimentacao.valor))\
        .filter(Movimentacao.tipo == "GANHO", Movimentacao.espaco_id == espaco_id)\
        .scalar() or 0

    return {"Total Ganhos": total}

def total_gastos(db: Session, espaco_id: int):

    total = db.query(func.sum(Movimentacao.valor))\
        .filter(Movimentacao.tipo == "GASTO", Movimentacao.espaco_id == espaco_id)\
        .scalar() or 0

    return {"Total Gastos": total}

def buscar_id(db: Session, id: int, espaco_id: int):

    movimentacao = (
        db.query(Movimentacao)
        .filter(Movimentacao.id == id, Movimentacao.espaco_id == espaco_id)
        .first()
    )

    if not movimentacao:
        raise HTTPException(
            status_code=404,
            detail="Movimentação não encontrada"
        )

    return movimentacao

def buscar_por_data(db: Session, data: date, espaco_id: int):

    movimentacoes = (
        db.query(Movimentacao)
        .filter(Movimentacao.data == data, Movimentacao.espaco_id == espaco_id)
        .all()
    )

    if not movimentacoes:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma movimentação encontrada para essa data."
        )

    return movimentacoes

def buscar_periodo(
    db: Session,
    data_inicio: date,
    data_fim: date,
    espaco_id: int
):

    return (
        db.query(Movimentacao)
        .filter(
            Movimentacao.data >= data_inicio,
            Movimentacao.data <= data_fim,
            Movimentacao.espaco_id == espaco_id
        )
        .all()
    )

def quantidade_movimentacoes(db: Session, espaco_id: int):

    quantidade = db.query(Movimentacao).filter(Movimentacao.espaco_id == espaco_id).count()

    return {
        "Quantidade de movimentações": quantidade
    }
