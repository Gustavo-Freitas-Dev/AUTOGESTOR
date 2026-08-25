"""add password reset tokens and token version

Revision ID: 20260825_03
Revises: 20260825_02
Create Date: 2026-08-25 15:30:00
"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260825_03"
down_revision: str | Sequence[str] | None = "20260825_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("usuarios", "token_version", server_default=None)

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_reset_tokens_usuario_id", "password_reset_tokens", ["usuario_id"], unique=False)
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
    op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_expires_at", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_usuario_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_column("usuarios", "token_version")
