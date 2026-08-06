"""Migra o SQLite legado para espaços financeiros, preservando os dados."""

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


def migrar(caminho: Path, criar_backup: bool = True) -> Path | None:
    caminho = caminho.resolve()
    if not caminho.exists():
        raise FileNotFoundError(f"Banco não encontrado: {caminho}")

    backup = None
    if criar_backup:
        carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = caminho.with_name(f"{caminho.stem}.backup_{carimbo}{caminho.suffix}")
        shutil.copy2(caminho, backup)

    con = sqlite3.connect(caminho)
    con.execute("PRAGMA foreign_keys = OFF")
    try:
        colunas = {linha[1] for linha in con.execute("PRAGMA table_info(movimentacoes)")}
        if {"espaco_id", "criado_por_id"}.issubset(colunas):
            return backup
        if "usuario_id" not in colunas:
            raise RuntimeError("A tabela movimentacoes não possui usuario_id; migração manual necessária.")

        con.execute("BEGIN IMMEDIATE")
        tabelas = {linha[0] for linha in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for tabela in ("membros_espacos", "espacos_financeiros"):
            if tabela in tabelas and con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0] > 0:
                raise RuntimeError(f"A tabela {tabela} já contém dados; migração automática interrompida.")
        con.execute("DROP TABLE IF EXISTS membros_espacos")
        con.execute("DROP TABLE IF EXISTS espacos_financeiros")
        con.execute("DROP INDEX IF EXISTS ix_espacos_financeiros_tipo")
        con.execute("DROP INDEX IF EXISTS ix_espacos_financeiros_codigo_acesso")
        con.execute("DROP INDEX IF EXISTS ix_membros_espacos_usuario_id")
        con.execute("DROP INDEX IF EXISTS ix_membros_espacos_espaco_id")
        con.executescript("""
            CREATE TABLE espacos_financeiros (
                id INTEGER PRIMARY KEY,
                nome VARCHAR(80) NOT NULL,
                tipo VARCHAR(12) NOT NULL CHECK (tipo IN ('PESSOAL','COMPARTILHADO')),
                codigo_acesso VARCHAR(8) UNIQUE,
                codigo_ativo BOOLEAN NOT NULL DEFAULT 0,
                limite_membros INTEGER NOT NULL DEFAULT 5,
                criado_por_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
                criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX ix_espacos_financeiros_tipo ON espacos_financeiros(tipo);
            CREATE UNIQUE INDEX ix_espacos_financeiros_codigo_acesso ON espacos_financeiros(codigo_acesso);

            CREATE TABLE membros_espacos (
                id INTEGER PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                espaco_id INTEGER NOT NULL REFERENCES espacos_financeiros(id) ON DELETE CASCADE,
                papel VARCHAR(7) NOT NULL CHECK (papel IN ('DONO','ADMIN','MEMBRO')),
                entrou_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_membro_usuario_espaco UNIQUE (usuario_id, espaco_id)
            );
            CREATE INDEX ix_membros_espacos_usuario_id ON membros_espacos(usuario_id);
            CREATE INDEX ix_membros_espacos_espaco_id ON membros_espacos(espaco_id);

            INSERT INTO espacos_financeiros
                (nome, tipo, codigo_acesso, codigo_ativo, limite_membros, criado_por_id)
            SELECT 'Meu espaço', 'PESSOAL', NULL, 0, 1, id FROM usuarios;

            INSERT INTO membros_espacos (usuario_id, espaco_id, papel)
            SELECT criado_por_id, id, 'DONO' FROM espacos_financeiros WHERE tipo = 'PESSOAL';

            CREATE TABLE movimentacoes_novas (
                id INTEGER PRIMARY KEY,
                espaco_id INTEGER NOT NULL REFERENCES espacos_financeiros(id) ON DELETE CASCADE,
                criado_por_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
                tipo VARCHAR(5) NOT NULL CHECK (tipo IN ('GANHO','GASTO')),
                categoria VARCHAR NOT NULL,
                descricao VARCHAR,
                valor NUMERIC(12,2) NOT NULL,
                data DATE NOT NULL
            );

            INSERT INTO movimentacoes_novas
                (id, espaco_id, criado_por_id, tipo, categoria, descricao, valor, data)
            SELECT m.id, e.id, m.usuario_id, m.tipo, m.categoria, m.descricao, ROUND(m.valor, 2), m.data
            FROM movimentacoes m
            JOIN espacos_financeiros e ON e.criado_por_id = m.usuario_id AND e.tipo = 'PESSOAL';
        """)

        antigas = con.execute("SELECT COUNT(*) FROM movimentacoes").fetchone()[0]
        novas = con.execute("SELECT COUNT(*) FROM movimentacoes_novas").fetchone()[0]
        if antigas != novas:
            raise RuntimeError(f"Contagem divergente: {antigas} registros antigos e {novas} migrados.")

        con.executescript("""
            DROP TABLE movimentacoes;
            ALTER TABLE movimentacoes_novas RENAME TO movimentacoes;
            CREATE INDEX ix_movimentacoes_espaco_id ON movimentacoes(espaco_id);
            CREATE INDEX ix_movimentacoes_criado_por_id ON movimentacoes(criado_por_id);
        """)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return backup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--banco", default="autogestor.db")
    parser.add_argument("--sem-backup", action="store_true", help="Use somente em cópias descartáveis.")
    args = parser.parse_args()
    resultado = migrar(Path(args.banco), criar_backup=not args.sem_backup)
    print("Migração concluída.")
    if resultado:
        print(f"Backup criado em: {resultado}")
