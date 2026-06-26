from sqlalchemy import Column, Integer, String, Float, Date, Enum
from app.database.base import Base
from app.schemas.movimentacao_schemas import TipoMovimentacao

class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    id = Column(Integer, primary_key=True)
    tipo = Column(Enum(TipoMovimentacao), nullable=False)       # GANHO ou GASTO
    categoria = Column(String, nullable=False)
    descricao = Column(String)
    valor = Column(Float, nullable=False)
    data = Column(Date, nullable=False)