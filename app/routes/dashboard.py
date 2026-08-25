from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.auth_dependencies import obter_usuario_atual
from app.database.dependencies import get_db
from app.models.usuario_model import Usuario
from app.services.dashboard_service import (
    buscar_id as service_buscar_id,
)
from app.services.dashboard_service import (
    buscar_periodo as service_buscar_periodo,
)
from app.services.dashboard_service import (
    buscar_por_data as service_buscar_por_data,
)
from app.services.dashboard_service import (
    quantidade_movimentacoes as service_quantidade_movimentacoes,
)
from app.services.dashboard_service import (
    saldo_total,
)
from app.services.dashboard_service import (
    total_ganhos as service_total_ganhos,
)
from app.services.dashboard_service import (
    total_gastos as service_total_gastos,
)
from app.services.espaco_service import verificar_acesso_espaco

router = APIRouter(prefix="/espacos/{espaco_id}/dashboard", tags=["Dashboard"])

@router.get('/resumo')
def resumo(espaco_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(obter_usuario_atual)):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    return {
        **saldo_total(db, espaco_id), **service_total_ganhos(db, espaco_id),
        **service_total_gastos(db, espaco_id), **service_quantidade_movimentacoes(db, espaco_id)
    }


@router.get('/resumo-mensal')
def resumo_mensal(
    espaco_id: int,
    ano: int,
    mes: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    if mes < 1 or mes > 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Mes deve estar entre 1 e 12.',
        )
    data_inicio = date(ano, mes, 1)
    if mes == 12:
        data_fim = date(ano + 1, 1, 1)
    else:
        data_fim = date(ano, mes + 1, 1)
    movimentos = service_buscar_periodo(db, data_inicio, data_fim, espaco_id)

    ganhos = sum(mov.valor for mov in movimentos if str(mov.tipo) == 'GANHO')
    gastos = sum(mov.valor for mov in movimentos if str(mov.tipo) == 'GASTO')
    return {
        'ano': ano,
        'mes': mes,
        'total_ganhos': ganhos,
        'total_gastos': gastos,
        'saldo': ganhos - gastos,
        'quantidade_movimentacoes': len(movimentos),
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
