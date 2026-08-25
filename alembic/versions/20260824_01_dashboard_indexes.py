"""add dashboard indexes safely

Revision ID: 20260824_01
Revises:
Create Date: 2026-08-24 00:00:00
"""

from typing import Sequence

from alembic import op

revision: str = "20260824_01"
down_revision: str | Sequence[str] | None = "20260825_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_movimentacoes_data ON movimentacoes(data)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_movimentacoes_tipo ON movimentacoes(tipo)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_movimentacoes_categoria ON movimentacoes(categoria)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_movimentacoes_data")
    op.execute("DROP INDEX IF EXISTS ix_movimentacoes_tipo")
    op.execute("DROP INDEX IF EXISTS ix_movimentacoes_categoria")
