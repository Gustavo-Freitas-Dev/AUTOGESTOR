from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base
from app.models.enums import TipoEspaco


class EspacoFinanceiro(Base):
    __tablename__ = "espacos_financeiros"

    id = Column(Integer, primary_key=True)
    nome = Column(String(80), nullable=False)
    tipo = Column(Enum(TipoEspaco), nullable=False, index=True)
    codigo_acesso = Column(String(8), unique=True, nullable=True, index=True)
    codigo_ativo = Column(Boolean, nullable=False, default=False)
    limite_membros = Column(Integer, nullable=False, default=5)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    criador = relationship("Usuario", foreign_keys=[criado_por_id], back_populates="espacos_criados")
    membros = relationship("MembroEspaco", back_populates="espaco", cascade="all, delete-orphan")
    movimentacoes = relationship("Movimentacao", back_populates="espaco", cascade="all, delete-orphan")
