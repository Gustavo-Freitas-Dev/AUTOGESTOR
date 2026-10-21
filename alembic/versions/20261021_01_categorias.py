"""Categorias personalizadas por espaço financeiro.

Revision ID: 20261021_01
Revises: 20260824_01
"""
from alembic import op
import sqlalchemy as sa

revision = "20261021_01"
down_revision = "20260824_01"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("espaco_id", sa.Integer(), sa.ForeignKey("espacos_financeiros.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(length=80), nullable=False),
        sa.Column("nome_normalizado", sa.String(length=80), nullable=False),
        sa.UniqueConstraint("espaco_id", "nome_normalizado", name="uq_categorias_espaco_nome"),
    )
    op.create_index("ix_categorias_espaco_id", "categorias", ["espaco_id"])

def downgrade():
    op.drop_index("ix_categorias_espaco_id", table_name="categorias")
    op.drop_table("categorias")
