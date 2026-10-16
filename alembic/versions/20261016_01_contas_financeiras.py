"""Create accounts and optional account link for existing movements."""
from alembic import op
import sqlalchemy as sa

revision = "20261016_01"
down_revision = "20260825_03"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "contas_financeiras",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("espaco_id", sa.Integer, sa.ForeignKey("espacos_financeiros.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("tipo", sa.Enum("BANCO", "CARTEIRA", name="tipoconta"), nullable=False),
        sa.Column("ambiente", sa.Enum("PESSOAL", "MOTORISTA", name="ambientefinanceiro"), nullable=False),
        sa.Column("saldo_inicial", sa.Numeric(12, 2), nullable=False),
        sa.UniqueConstraint("id", "espaco_id", name="uq_conta_id_espaco"),
    )
    op.create_index("ix_contas_financeiras_espaco_id", "contas_financeiras", ["espaco_id"])
    with op.batch_alter_table("movimentacoes") as batch:
        batch.add_column(sa.Column("conta_id", sa.Integer, nullable=True))
        batch.create_foreign_key(
            "fk_movimentacoes_conta_espaco", "contas_financeiras",
            ["conta_id", "espaco_id"], ["id", "espaco_id"],
        )
        batch.create_index("ix_movimentacoes_conta_id", ["conta_id"])


def downgrade():
    with op.batch_alter_table("movimentacoes") as batch:
        batch.drop_index("ix_movimentacoes_conta_id")
        batch.drop_constraint("fk_movimentacoes_conta_espaco", type_="foreignkey")
        batch.drop_column("conta_id")
    op.drop_index("ix_contas_financeiras_espaco_id", table_name="contas_financeiras")
    op.drop_table("contas_financeiras")
    sa.Enum(name="ambientefinanceiro").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="tipoconta").drop(op.get_bind(), checkfirst=True)
