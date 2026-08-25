"""create initial schema

Revision ID: 20260825_01
Revises:
Create Date: 2026-08-25 00:00:00
"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260825_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("senha_hash", sa.String(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usuarios_email"), "usuarios", ["email"], unique=True)
    op.create_index(op.f("ix_usuarios_id"), "usuarios", ["id"], unique=False)

    op.create_table(
        "espacos_financeiros",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=80), nullable=False),
        sa.Column("tipo", sa.Enum("PESSOAL", "COMPARTILHADO", name="tipoespaco"), nullable=False),
        sa.Column("codigo_acesso", sa.String(length=8), nullable=True),
        sa.Column("codigo_ativo", sa.Boolean(), nullable=False),
        sa.Column("limite_membros", sa.Integer(), nullable=False),
        sa.Column("criado_por_id", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_espacos_financeiros_codigo_acesso"), "espacos_financeiros", ["codigo_acesso"], unique=True)
    op.create_index(op.f("ix_espacos_financeiros_tipo"), "espacos_financeiros", ["tipo"], unique=False)

    op.create_table(
        "membros_espacos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("espaco_id", sa.Integer(), nullable=False),
        sa.Column("papel", sa.Enum("DONO", "ADMIN", "MEMBRO", name="papelmembro"), nullable=False),
        sa.Column("entrou_em", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["espaco_id"], ["espacos_financeiros.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id", "espaco_id", name="uq_membro_usuario_espaco"),
    )
    op.create_index(op.f("ix_membros_espacos_espaco_id"), "membros_espacos", ["espaco_id"], unique=False)
    op.create_index(op.f("ix_membros_espacos_usuario_id"), "membros_espacos", ["usuario_id"], unique=False)

    op.create_table(
        "movimentacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("espaco_id", sa.Integer(), nullable=False),
        sa.Column("criado_por_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.Enum("GANHO", "GASTO", name="tipomovimentacao"), nullable=False),
        sa.Column("categoria", sa.String(), nullable=False),
        sa.Column("descricao", sa.String(), nullable=True),
        sa.Column("valor", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["espaco_id"], ["espacos_financeiros.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_movimentacoes_criado_por_id"), "movimentacoes", ["criado_por_id"], unique=False)
    op.create_index(op.f("ix_movimentacoes_espaco_id"), "movimentacoes", ["espaco_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_movimentacoes_espaco_id"), table_name="movimentacoes")
    op.drop_index(op.f("ix_movimentacoes_criado_por_id"), table_name="movimentacoes")
    op.drop_table("movimentacoes")

    op.drop_index(op.f("ix_membros_espacos_usuario_id"), table_name="membros_espacos")
    op.drop_index(op.f("ix_membros_espacos_espaco_id"), table_name="membros_espacos")
    op.drop_table("membros_espacos")

    op.drop_index(op.f("ix_espacos_financeiros_tipo"), table_name="espacos_financeiros")
    op.drop_index(op.f("ix_espacos_financeiros_codigo_acesso"), table_name="espacos_financeiros")
    op.drop_table("espacos_financeiros")

    op.drop_index(op.f("ix_usuarios_id"), table_name="usuarios")
    op.drop_index(op.f("ix_usuarios_email"), table_name="usuarios")
    op.drop_table("usuarios")

    op.execute("DROP TYPE IF EXISTS tipomovimentacao")
    op.execute("DROP TYPE IF EXISTS papelmembro")
    op.execute("DROP TYPE IF EXISTS tipoespaco")