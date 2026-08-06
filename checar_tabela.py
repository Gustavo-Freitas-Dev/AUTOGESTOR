import sqlite3

con = sqlite3.connect('autogestor.db')
tabelas = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

print("Tabelas encontradas no banco:")
for t in tabelas:
    print(" -", t[0])

print()
print("Conteúdo da tabela 'usuarios':")
linhas = con.execute("SELECT id, nome, email FROM usuarios").fetchall()
if not linhas:
    print(" (vazia — nenhum usuário cadastrado ainda)")
else:
    for linha in linhas:
        print(" -", linha)

con.close()