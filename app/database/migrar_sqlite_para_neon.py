"""Copia os dados do SQLite local para o PostgreSQL configurado no Neon."""

from pathlib import Path

from sqlalchemy import create_engine, func, select, text

from app.database.base import Base
from app.database.db import DATABASE_URL
from app.database.db import engine as neon_engine
from app.models.espaco_financeiro import EspacoFinanceiro  # noqa: F401
from app.models.membro_espaco import MembroEspaco  # noqa: F401
from app.models.movimentacao import Movimentacao  # noqa: F401
from app.models.usuario_model import Usuario  # noqa: F401

SQLITE_PATH = Path("autogestor.db")


def migrar() -> None:
    if not SQLITE_PATH.exists():
        raise RuntimeError(f"Banco local não encontrado: {SQLITE_PATH.resolve()}")
    if DATABASE_URL.startswith("sqlite"):
        raise RuntimeError("DATABASE_URL não aponta para o Neon/PostgreSQL.")

    sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH}")
    Base.metadata.create_all(neon_engine)

    tabelas = list(Base.metadata.sorted_tables)
    with neon_engine.begin() as destino:
        ocupadas = {
            tabela.name: destino.execute(select(func.count()).select_from(tabela)).scalar_one()
            for tabela in tabelas
        }
        if any(ocupadas.values()):
            raise RuntimeError(
                "Migração cancelada: o banco Neon já possui dados. "
                f"Contagens: {ocupadas}"
            )

        with sqlite_engine.connect() as origem:
            for tabela in tabelas:
                registros = origem.execute(select(tabela)).mappings().all()
                if registros:
                    destino.execute(tabela.insert(), [dict(registro) for registro in registros])

        # IDs foram copiados explicitamente; sincroniza as sequences do PostgreSQL.
        for tabela in tabelas:
            if "id" not in tabela.c:
                continue
            destino.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{tabela.name}', 'id'), "
                    f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {tabela.name}"
                )
            )

    with neon_engine.connect() as conexao:
        totais = {
            tabela.name: conexao.execute(select(func.count()).select_from(tabela)).scalar_one()
            for tabela in tabelas
        }
    print(f"Migração concluída: {totais}")


if __name__ == "__main__":
    migrar()
