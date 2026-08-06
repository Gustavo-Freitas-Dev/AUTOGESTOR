from enum import Enum

class TipoMovimentacao(str, Enum):
    GANHO = "GANHO"
    GASTO = "GASTO"

from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from datetime import date

class CriarMovimentacao(BaseModel):
    tipo: TipoMovimentacao
    categoria: str = Field(min_length=1, max_length=80)
    descricao: str | None = Field(default=None, max_length=255)
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    data: date


class AtualizarMovimentacao(BaseModel):
    tipo: TipoMovimentacao
    categoria: str = Field(min_length=1, max_length=80)
    descricao: str | None = Field(default=None, max_length=255)
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    data: date


class MovimentacaoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    espaco_id: int
    criado_por_id: int
    tipo: TipoMovimentacao
    categoria: str
    descricao: str | None
    valor: Decimal
    data: date

