from pydantic import BaseModel, Field
from enum import Enum

class CategoriaGasto(str, Enum):
    combustivel = "COMBUSTIVEL"
    manutencao = "MANUTENCAO"
    operacional = "OPERACIONAL"
    pessoal = "PESSOAL"
    outros = "OUTROS"

class SubcategoriaGasto(str, Enum):
    oleo = "OLEO"
    pneu = "PNEU"
    freio = "FREIO"
    alinhamento = "ALINHAMENTO"
    revisao = "REVISAO"
    lavagem = "LAVAGEM"
    estacionamento = "ESTACIONAMENTO"
    pedagio = "PEDAGIO"
    alimentacao = "ALIMENTACAO"
    internet = "INTERNET"
    celular = "CELULAR"
    multa = "MULTA"
    imprevisto = "IMPREVISTO"

class CriarGastos(BaseModel):
    categoria: CategoriaGasto
    descricao: str = Field(..., example='posto ipiranga')
    valor: float = Field(..., example=50.84)

class AtualizarGastos(BaseModel):
    categoria: CategoriaGasto
    descricao: str = Field(..., example='Academia')
    valor: float = Field(..., example=62.85)