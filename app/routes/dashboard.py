from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
from app.database.dependencies import get_db
from app.database.auth_dependencies import obter_usuario_atual
from app.models.usuario_model import Usuario
from app.services.espaco_service import verificar_acesso_espaco
from app.services.dashboard_service import (
    saldo_total,
    total_gastos as service_total_gastos,
    total_ganhos as service_total_ganhos,
    buscar_id as service_buscar_id,
    buscar_por_data as service_buscar_por_data,
    buscar_periodo as service_buscar_periodo,
    quantidade_movimentacoes as service_quantidade_movimentacoes
)

router = APIRouter(prefix="/espacos/{espaco_id}/dashboard", tags=["Dashboard"])

@router.get('/resumo')
def resumo(espaco_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return {
        **saldo_total(db, espaco_id), **service_total_ganhos(db, espaco_id),
        **service_total_gastos(db, espaco_id), **service_quantidade_movimentacoes(db, espaco_id)
    }

@router.get("/saldo")
def saldo(espaco_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return saldo_total(db, espaco_id)


@router.get("/total_gastos")
def total_gastos(espaco_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_total_gastos(db, espaco_id)


@router.get("/total_ganhos")
def total_ganhos(espaco_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_total_ganhos(db, espaco_id)


@router.get("/data/{data}")
def buscar_data(
    espaco_id: int,
    data: date,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_buscar_por_data(db, data, espaco_id)


@router.get("/periodo")
def buscar_periodo(
    espaco_id: int,
    data_inicio: date,
    data_fim: date,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_buscar_periodo(db, data_inicio, data_fim, espaco_id)


@router.get("/{id}")
def buscar_id(espaco_id: int, id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return service_buscar_id(db, id, espaco_id)
