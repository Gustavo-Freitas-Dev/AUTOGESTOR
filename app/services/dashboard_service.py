from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.movimentacao import Movimentacao


def _to_decimal(valor: Decimal | int | float | None) -> Decimal:
    if valor is None:
        return Decimal("0.00")
    return Decimal(valor).quantize(Decimal("0.01"))


def resumo_dashboard(db: Session, espaco_id: int) -> dict[str, Decimal | int]:
    ganhos = func.coalesce(
        func.sum(case((Movimentacao.tipo == "GANHO", Movimentacao.valor), else_=0)),
        0,
    )
    gastos = func.coalesce(
        func.sum(case((Movimentacao.tipo == "GASTO", Movimentacao.valor), else_=0)),
        0,
    )
    quantidade = func.count(Movimentacao.id)
    total_ganhos, total_gastos, quantidade_movimentacoes = db.query(
        ganhos,
        gastos,
        quantidade,
    ).filter(Movimentacao.espaco_id == espaco_id).one()

    total_ganhos_decimal = _to_decimal(total_ganhos)
    total_gastos_decimal = _to_decimal(total_gastos)
    saldo = total_ganhos_decimal - total_gastos_decimal
    return {
        "Saldo": saldo,
        "saldo": saldo,
        "Total Ganhos": total_ganhos_decimal,
        "total_ganhos": total_ganhos_decimal,
        "Total Gastos": total_gastos_decimal,
        "total_gastos": total_gastos_decimal,
        "Quantidade de movimentações": quantidade_movimentacoes,
        "quantidade_movimentacoes": quantidade_movimentacoes,
    }

def saldo_total(db: Session, espaco_id: int):
    resumo = resumo_dashboard(db, espaco_id)
    saldo = resumo["saldo"]
    return {"Saldo": saldo, "saldo": saldo}

def total_ganhos(db: Session, espaco_id: int):
    resumo = resumo_dashboard(db, espaco_id)
    total_decimal = resumo["total_ganhos"]
    return {"Total Ganhos": total_decimal, "total_ganhos": total_decimal}

def total_gastos(db: Session, espaco_id: int):
    resumo = resumo_dashboard(db, espaco_id)
    total_decimal = resumo["total_gastos"]
    return {"Total Gastos": total_decimal, "total_gastos": total_decimal}

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

    if data_inicio > data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A data inicial nao pode ser maior que a data final.",
        )

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
    resumo = resumo_dashboard(db, espaco_id)
    quantidade = resumo["quantidade_movimentacoes"]
    return {"Quantidade de movimentações": quantidade, "quantidade_movimentacoes": quantidade}
