from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AmbienteFinanceiro, TipoConta


class CriarConta(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    tipo: TipoConta
    ambiente: AmbienteFinanceiro
    saldo_inicial: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)


class ContaResposta(CriarConta):
    model_config = ConfigDict(from_attributes=True)
    id: int
    espaco_id: int


class SaldoConta(ContaResposta):
    saldo_atual: Decimal
