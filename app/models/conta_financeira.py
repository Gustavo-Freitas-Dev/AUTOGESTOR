from sqlalchemy import Column, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.models.enums import AmbienteFinanceiro, TipoConta


class ContaFinanceira(Base):
    __tablename__ = "contas_financeiras"
    __table_args__ = (UniqueConstraint("id", "espaco_id", name="uq_conta_id_espaco"),)

    id = Column(Integer, primary_key=True)
    espaco_id = Column(Integer, ForeignKey("espacos_financeiros.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(80), nullable=False)
    tipo = Column(Enum(TipoConta), nullable=False)
    ambiente = Column(Enum(AmbienteFinanceiro), nullable=False)
    saldo_inicial = Column(Numeric(12, 2), nullable=False, default=0)

    espaco = relationship("EspacoFinanceiro")
