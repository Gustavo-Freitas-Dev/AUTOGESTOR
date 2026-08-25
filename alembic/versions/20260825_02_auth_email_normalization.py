"""normalize auth emails and add case-insensitive uniqueness

Revision ID: 20260825_02
Revises: 20260824_01
Create Date: 2026-08-25 12:00:00
"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260825_02"
down_revision: str | Sequence[str] | None = "20260824_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE usuarios SET email = lower(trim(email)) WHERE email IS NOT NULL")

    bind = op.get_bind()
    duplicados = bind.execute(
        sa.text(
            """
            SELECT lower(email) AS email_normalizado, COUNT(*) AS total
            FROM usuarios
            GROUP BY lower(email)
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()

    if duplicados:
        raise RuntimeError(
            "Migracao interrompida: existem emails duplicados quando normalizados. "
            "Corrija manualmente antes de aplicar esta revisao."
        )

    with op.batch_alter_table("usuarios") as batch_op:
        batch_op.alter_column("email", existing_type=sa.String(), type_=sa.String(length=320), existing_nullable=False)
        batch_op.alter_column("senha_hash", existing_type=sa.String(), type_=sa.String(length=255), existing_nullable=False)

    op.create_index(
        "ux_usuarios_email_lower",
        "usuarios",
        [sa.text("lower(email)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_usuarios_email_lower", table_name="usuarios")

    with op.batch_alter_table("usuarios") as batch_op:
        batch_op.alter_column("senha_hash", existing_type=sa.String(length=255), type_=sa.String(), existing_nullable=False)
        batch_op.alter_column("email", existing_type=sa.String(length=320), type_=sa.String(), existing_nullable=False)
