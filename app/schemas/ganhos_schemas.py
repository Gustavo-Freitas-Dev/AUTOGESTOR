from pydantic import BaseModel, Field

class CriarGanho(BaseModel):
    plataforma: str = Field(..., example='Uber')
    valor: float = Field(..., example=150.75)

class AtualizarGanho(BaseModel):
    plataforma: str = Field(..., example='Uber')
    valor: float = Field(..., example=150.75)