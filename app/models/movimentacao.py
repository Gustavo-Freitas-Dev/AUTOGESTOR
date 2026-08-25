from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.schemas.movimentacao_schemas import TipoMovimentacao


class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    id = Column(Integer, primary_key=True)

    # ── NOVO CAMPO ──────────────────────────────────────────────
    # Liga cada movimentação a um usuário específico. Sem isso,
    # a query "listar todas" trazia movimentações de TODOS os
    # usuários misturadas — por isso todo mundo via a mesma lista.
    #
    # nullable=True (por enquanto): registros antigos no banco
    # foram criados antes desse campo existir, então não têm
    # usuario_id ainda. Depois de rodar o script de migração
    # (atribuir_movimentacoes_antigas.py), você pode trocar para
    # nullable=False com segurança, se quiser reforçar a regra.
    espaco_id = Column(Integer, ForeignKey("espacos_financeiros.id", ondelete="CASCADE"), nullable=False, index=True)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False, index=True)

    tipo = Column(Enum(TipoMovimentacao), nullable=False)       # GANHO ou GASTO
    categoria = Column(String, nullable=False)
    descricao = Column(String)
    valor = Column(Numeric(12, 2), nullable=False)
    data = Column(Date, nullable=False)

    espaco = relationship("EspacoFinanceiro", back_populates="movimentacoes")
    criador = relationship("Usuario", foreign_keys=[criado_por_id], back_populates="movimentacoes_criadas")
