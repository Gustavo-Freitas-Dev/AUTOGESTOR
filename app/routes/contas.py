from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.auth_dependencies import obter_usuario_atual
from app.database.dependencies import get_db
from app.models.conta_financeira import ContaFinanceira
from app.models.movimentacao import Movimentacao
from app.models.usuario_model import Usuario
from app.schemas.conta_schemas import ContaResposta, CriarConta, SaldoConta
from app.schemas.movimentacao_schemas import TipoMovimentacao
from app.services.espaco_service import verificar_acesso_espaco

router = APIRouter(prefix="/espacos/{espaco_id}/contas", tags=["Contas financeiras"])


@router.post("/", response_model=ContaResposta, status_code=201)
def criar_conta(
    espaco_id: int,
    dado: CriarConta,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    conta = ContaFinanceira(espaco_id=espaco_id, **dado.model_dump())
    db.add(conta)
    db.commit()
    db.refresh(conta)
    return conta


@router.get("/", response_model=list[SaldoConta])
def listar_contas(
    espaco_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual),
):
    verificar_acesso_espaco(usuario.id, espaco_id, db)
    contas = db.scalars(
        select(ContaFinanceira).where(ContaFinanceira.espaco_id == espaco_id)
        .order_by(ContaFinanceira.id)
    ).all()
    resposta = []
    for conta in contas:
        ganhos = db.scalar(select(func.coalesce(func.sum(Movimentacao.valor), 0)).where(
            Movimentacao.espaco_id == espaco_id,
            Movimentacao.conta_id == conta.id,
            Movimentacao.tipo == TipoMovimentacao.GANHO,
        ))
        gastos = db.scalar(select(func.coalesce(func.sum(Movimentacao.valor), 0)).where(
            Movimentacao.espaco_id == espaco_id,
            Movimentacao.conta_id == conta.id,
            Movimentacao.tipo == TipoMovimentacao.GASTO,
        ))
        saldo = Decimal(conta.saldo_inicial) + Decimal(ganhos or 0) - Decimal(gastos or 0)
        resposta.append(SaldoConta.model_validate(conta, from_attributes=True).model_copy(
            update={"saldo_atual": saldo}
        ))
    return resposta
