from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from app.database.base import Base

class Categoria(Base):
    __tablename__ = "categorias"
    __table_args__ = (UniqueConstraint("espaco_id", "nome_normalizado", name="uq_categorias_espaco_nome"),)
    id = Column(Integer, primary_key=True)
    espaco_id = Column(Integer, ForeignKey("espacos_financeiros.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(80), nullable=False)
    nome_normalizado = Column(String(80), nullable=False)
