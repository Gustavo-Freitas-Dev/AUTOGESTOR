"""
corrigir_banco.py
──────────────────────────────────────────────────────────────
Script de diagnóstico e correção completa do banco autogestor.db.

Executa tudo em ordem:
  1. Mostra o estado atual do banco (tabelas e colunas existentes)
  2. Adiciona a coluna usuario_id em movimentacoes (se não existir)
  3. Vincula movimentações órfãs ao primeiro usuário cadastrado
  4. Confirma o estado final

COMO RODAR (na raiz do projeto, com o servidor PARADO):
  python corrigir_banco.py
"""

import sqlite3

print("=" * 55)
print("  DIAGNÓSTICO E CORREÇÃO DO BANCO autogestor.db")
print("=" * 55)

con = sqlite3.connect("autogestor.db")
cur = con.cursor()

# ── 1. ESTADO ATUAL ──────────────────────────────────────────
print("\n📋 TABELAS ENCONTRADAS:")
tabelas = cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()
for t in tabelas:
    print(f"   - {t[0]}")

print("\n📋 COLUNAS DA TABELA movimentacoes:")
colunas_mov = cur.execute("PRAGMA table_info(movimentacoes)").fetchall()
nomes_colunas = [c[1] for c in colunas_mov]
for c in colunas_mov:
    print(f"   - {c[1]} ({c[2]})")

print("\n📋 COLUNAS DA TABELA usuarios:")
try:
    colunas_usr = cur.execute("PRAGMA table_info(usuarios)").fetchall()
    for c in colunas_usr:
        print(f"   - {c[1]} ({c[2]})")
except Exception as e:
    print(f"   ❌ Tabela usuarios não encontrada: {e}")

# ── 2. ADICIONAR usuario_id SE NÃO EXISTIR ───────────────────
print("\n🔧 APLICANDO CORREÇÕES...")

if "usuario_id" not in nomes_colunas:
    try:
        cur.execute(
            "ALTER TABLE movimentacoes ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id)"
        )
        con.commit()
        print("   ✅ Coluna usuario_id adicionada em movimentacoes")
    except Exception as e:
        print(f"   ❌ Erro ao adicionar coluna: {e}")
else:
    print("   ✅ Coluna usuario_id já existe em movimentacoes")

# ── 3. VINCULAR MOVIMENTAÇÕES ÓRFÃS AO PRIMEIRO USUÁRIO ──────
usuario = cur.execute(
    "SELECT id, nome, email FROM usuarios ORDER BY id ASC LIMIT 1"
).fetchone()

if not usuario:
    print("\n   ⚠️  Nenhum usuário encontrado no banco.")
    print("      Cadastre uma conta pelo login.html primeiro.")
    print("      Depois rode este script novamente para vincular as movimentações.")
else:
    usuario_id, nome, email = usuario
    print(f"\n   👤 Usuário encontrado: {nome} ({email}) — id {usuario_id}")

    orfas = cur.execute(
        "SELECT COUNT(*) FROM movimentacoes WHERE usuario_id IS NULL"
    ).fetchone()[0]

    if orfas > 0:
        cur.execute(
            "UPDATE movimentacoes SET usuario_id = ? WHERE usuario_id IS NULL",
            (usuario_id,)
        )
        con.commit()
        print(f"   ✅ {orfas} movimentações vinculadas a {nome}")
    else:
        print("   ✅ Nenhuma movimentação órfã — tudo vinculado corretamente")

# ── 4. ESTADO FINAL ──────────────────────────────────────────
print("\n" + "=" * 55)
print("  ESTADO FINAL DO BANCO")
print("=" * 55)

print("\n📋 TABELAS:")
tabelas = cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()
for t in tabelas:
    count = cur.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
    print(f"   - {t[0]}: {count} registro(s)")

print("\n📋 COLUNAS DA TABELA movimentacoes (estado final):")
for c in cur.execute("PRAGMA table_info(movimentacoes)").fetchall():
    print(f"   - {c[1]} ({c[2]})")

print("\n📋 USUÁRIOS CADASTRADOS:")
usuarios = cur.execute("SELECT id, nome, email FROM usuarios").fetchall()
if not usuarios:
    print("   (nenhum usuário ainda)")
else:
    for u in usuarios:
        total_mov = cur.execute(
            "SELECT COUNT(*) FROM movimentacoes WHERE usuario_id = ?", (u[0],)
        ).fetchone()[0]
        print(f"   - [{u[0]}] {u[1]} ({u[2]}) — {total_mov} movimentação(ões)")

print("\n✅ Script finalizado.\n")
con.close()  