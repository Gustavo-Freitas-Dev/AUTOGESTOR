from pydantic import BaseModel, Field

class CriarGastos(BaseModel):
    tipo: str = Field(..., example='Combustível')
    valor: float = Field(..., example=50.84)

