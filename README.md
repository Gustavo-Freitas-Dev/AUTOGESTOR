# AutoGestor

AutoGestor e uma API de controle financeiro com FastAPI, SQLAlchemy e frontend estatico. O projeto esta preparado para portfolio e deploy em ambiente serverless com PostgreSQL.

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2 (sync)
- Alembic
- Pydantic v2
- PostgreSQL (producao)
- SQLite (apenas dev local opcional)
- Pytest, Ruff, MyPy

## Arquitetura

- `app/routes`: camada HTTP
- `app/services`: regras de negocio
- `app/models`: modelos ORM
- `app/schemas`: contratos de entrada/saida
- `app/database`: engine, sessao e scripts de migracao
- `app/core`: configuracao e tratamento global de erros
- `app/static`: frontend

## Politica de Banco (importante)

- Em producao/Vercel, `DATABASE_URL` e obrigatoria.
- Em producao/Vercel, `DATABASE_URL` deve ser PostgreSQL.
- Fallback para SQLite existe apenas em desenvolvimento local.
- Startup da aplicacao nao usa `create_all`; schema e gerenciado por Alembic.

## Variaveis de Ambiente

Copie `.env.example` para `.env.local`.

```env
AUTOGESTOR_APP_ENV=development
DATABASE_URL=
AUTOGESTOR_ALLOW_SQLITE_FALLBACK=true
AUTOGESTOR_SECRET_KEY=troque-esta-chave
AUTOGESTOR_ACCESS_TOKEN_EXPIRE_MINUTES=10080
AUTOGESTOR_CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
```

## Provedores PostgreSQL (exemplos)

- Neon
- Supabase
- Railway
- Vercel Postgres

A maioria fornece URL no formato `postgres://` ou `postgresql://`. O app normaliza automaticamente para o driver `psycopg`.

## Setup Local

```powershell
uv sync --dev
uv run alembic upgrade head
uv run uvicorn main:app --reload
```

Acessos:

- Frontend: `http://127.0.0.1:8000/static/login.html`
- Docs: `http://127.0.0.1:8000/docs`
- Healthcheck: `http://127.0.0.1:8000/health`

## Fluxo de Migracoes (Alembic-first)

Criar migration:

```powershell
uv run alembic revision -m "descricao"
```

Aplicar migration:

```powershell
uv run alembic upgrade head
```

Ver revisao atual:

```powershell
uv run alembic current
```

Ver historico:

```powershell
uv run alembic history
```

Rollback de 1 revisao:

```powershell
uv run alembic downgrade -1
```

## Migracao Segura SQLite -> PostgreSQL

Pre-condicoes:

1. Configurar `DATABASE_URL` PostgreSQL.
2. Executar schema no alvo com Alembic (`upgrade head`).
3. Garantir backup do SQLite.

Executar copia de dados:

```powershell
uv run python app/database/migrar_sqlite_para_neon.py
```

Comportamento do script:

- Aborta se `DATABASE_URL` nao for PostgreSQL.
- Aborta se banco destino ja possuir dados.
- Copia tabela por tabela mantendo IDs.
- Sincroniza sequences no PostgreSQL.

## Backup e Restore (referencia)

Backup PostgreSQL:

```powershell
pg_dump "$env:DATABASE_URL" -Fc -f backup_autogestor.dump
```

Restore PostgreSQL:

```powershell
pg_restore --clean --if-exists --no-owner --no-privileges -d "$env:DATABASE_URL" backup_autogestor.dump
```

Backup SQLite local:

```powershell
Copy-Item autogestor.db autogestor.backup.db
```

## Validacao Pos-Deploy

1. Conferir `GET /health` retorna `200`.
2. Criar conta nova no `login.html`.
3. Entrar no dashboard com essa conta.
4. Criar uma movimentacao.
5. Editar a movimentacao e confirmar que a sessao permanece ativa.
6. Sair voluntariamente pelo menu de perfil.
7. Entrar novamente com o mesmo e-mail e senha.
8. Confirmar que o usuario continua existente e que a edicao permaneceu.
9. Abrir janela anonima e repetir login para validar persistencia entre sessoes.
10. Fazer redeploy na Vercel.
11. Repetir login apos redeploy e validar dados preservados.
12. Executar `uv run alembic current` no ambiente e validar revisao esperada.

## Variaveis obrigatorias em producao

- `AUTOGESTOR_APP_ENV=production`
- `DATABASE_URL=<url-postgresql>`
- `AUTOGESTOR_SECRET_KEY=<segredo-forte-e-estavel>`

Se `DATABASE_URL` ou `AUTOGESTOR_SECRET_KEY` nao estiverem configuradas corretamente em producao/Vercel, a aplicacao falha na inicializacao por seguranca.

## Qualidade

```powershell
uv run ruff check .
uv run mypy app/core
uv run pytest -q
```

## Teste de Integracao PostgreSQL

Defina uma URL exclusiva de teste:

```powershell
$env:AUTOGESTOR_TEST_DATABASE_URL="postgresql://.../autogestor_test"
uv run pytest -q -k postgres_integration
```

O teste aplica migrations, cria usuario, faz login, cria movimentacao,
reinicia engine/sessoes e valida novo login com dados persistidos.

## Deploy Vercel

- Runtime Python definido em `vercel.json`.
- Configure no projeto Vercel:
  - `AUTOGESTOR_APP_ENV=production`
  - `DATABASE_URL=<url-postgresql>`
  - `AUTOGESTOR_SECRET_KEY=<segredo-forte>`
  - `AUTOGESTOR_CORS_ORIGINS=<origens-permitidas>`

Sem `DATABASE_URL` em producao, a aplicacao falha por seguranca.

No startup, a aplicacao registra somente o dialeto ativo (exemplo: `Database dialect: postgresql`), sem expor credenciais.

## Roteiro de Validacao do Login em Producao

1. Criar conta nova.
2. Anotar apenas o e-mail (nunca registrar senha em logs).
3. Sair voluntariamente.
4. Entrar novamente.
5. Criar movimentacao.
6. Editar movimentacao.
7. Sair novamente.
8. Entrar novamente.
9. Abrir janela anonima e entrar.
10. Fazer redeploy.
11. Entrar novamente e validar usuario + movimentacao preservados.
12. Confirmar no painel do PostgreSQL que o usuario continua existente.
