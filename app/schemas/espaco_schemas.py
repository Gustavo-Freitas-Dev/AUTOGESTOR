from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import PapelMembro, TipoEspaco


class CriarEspacoCompartilhado(BaseModel):
    nome: str = Field(min_length=2, max_length=80)
    limite_membros: int = Field(default=5, ge=2, le=20)


class AtualizarEspaco(BaseModel):
    nome: str = Field(min_length=2, max_length=80)
    codigo_ativo: bool | None = None
    limite_membros: int | None = Field(default=None, ge=2, le=20)


class EntrarEspaco(BaseModel):
    codigo: str = Field(min_length=8, max_length=8)


class MembroResposta(BaseModel):
    usuario_id: int
    nome: str
    email: str
    papel: PapelMembro
    entrou_em: datetime


class EspacoResumo(BaseModel):
    id: int
    nome: str
    tipo: TipoEspaco
    papel: PapelMembro
    quantidade_membros: int
    limite_membros: int
    codigo_acesso: str | None = None
    codigo_ativo: bool


class EspacoDetalhe(EspacoResumo):
    limite_membros: int
    criado_por_id: int
    criado_em: datetime


class CodigoRegenerado(BaseModel):
    espaco_id: int
    codigo_acesso: str
