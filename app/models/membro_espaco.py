from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base
from app.models.enums import PapelMembro


class MembroEspaco(Base):
    __tablename__ = "membros_espacos"
    __table_args__ = (UniqueConstraint("usuario_id", "espaco_id", name="uq_membro_usuario_espaco"),)

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    espaco_id = Column(Integer, ForeignKey("espacos_financeiros.id", ondelete="CASCADE"), nullable=False, index=True)
    papel = Column(Enum(PapelMembro), nullable=False)
    entrou_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    usuario = relationship("Usuario", back_populates="membros_espacos")
    espaco = relationship("EspacoFinanceiro", back_populates="membros")
