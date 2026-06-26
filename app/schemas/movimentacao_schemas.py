from enum import Enum

class TipoMovimentacao(str, Enum):
    GANHO = "GANHO"
    GASTO = "GASTO"

from pydantic import BaseModel
from datetime import date

class CriarMovimentacao(BaseModel):
    tipo: TipoMovimentacao
    categoria: str
    descricao: str | None = None
    valor: float
    data: date


class AtualizarMovimentacao(BaseModel):
    tipo: TipoMovimentacao
    categoria: str
    descricao: str | None = None
    valor: float
    data: date

