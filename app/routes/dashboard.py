from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.services.movimentacao_service import (
    saldo_total,
    total_gastos as service_total_gastos,
    total_ganhos as service_total_ganhos
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/saldo")
def saldo(db: Session = Depends(get_db)):
    return saldo_total(db)


@router.get("/total_gastos")
def total_gastos(db: Session = Depends(get_db)):
    return service_total_gastos(db)


@router.get("/total_ganhos")
def total_ganhos(db: Session = Depends(get_db)):
    return service_total_ganhos(db)