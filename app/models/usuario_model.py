"""
app/models/usuario_model.py
─────────────────────────────
Model SQLAlchemy do usuário. Segue o mesmo padrão do seu
movimentacao_model.py — herda de Base (app/database/base.py).

CAMPOS:
  id              → chave primária
  nome            → nome de exibição do usuário
  email           → usado para login, precisa ser único
  senha_hash      → NUNCA guardamos a senha em texto puro.
                    Guardamos o hash (bcrypt) gerado no momento
                    do cadastro. Ver app/services/auth_service.py
                    para a lógica de hash/verificação.
  criado_em       → data de criação do registro, útil para
                    auditoria e para exibir "membro desde" no futuro
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)

    # unique=True garante a nível de banco que não existem dois
    # usuários com o mesmo e-mail — segunda camada de proteção
    # além da validação que já fazemos no service.
    email = Column(String, unique=True, index=True, nullable=False)

    senha_hash = Column(String, nullable=False)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    membros_espacos = relationship("MembroEspaco", back_populates="usuario", cascade="all, delete-orphan")
    espacos_criados = relationship("EspacoFinanceiro", foreign_keys="EspacoFinanceiro.criado_por_id", back_populates="criador")
    movimentacoes_criadas = relationship("Movimentacao", foreign_keys="Movimentacao.criado_por_id", back_populates="criador")
