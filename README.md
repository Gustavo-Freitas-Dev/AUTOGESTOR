# AutoGestor

AutoGestor e uma aplicacao de controle financeiro com FastAPI, SQLAlchemy e frontend em HTML/CSS/JS. O projeto foi estruturado para portfolio com foco em seguranca, organizacao, testes e preparo para deploy.

## Objetivo

Gerenciar ganhos e gastos com autenticacao JWT, isolamento de dados por usuario e espaco financeiro, dashboard e filtros analiticos.

## Principais Funcionalidades

- Cadastro e login com JWT
- Endpoint de usuario autenticado (`/auth/me`)
- Logout no cliente com invalidacao local de sessao
- Espacos pessoais e compartilhados (com codigo de acesso)
- CRUD de movimentacoes por espaco
- Filtros por tipo, categoria, descricao, periodo
- Ordenacao e paginacao na listagem
- Resumo financeiro, resumo mensal e resumo por categoria
- Dashboard visual com frontend responsivo
- Exportacao CSV/Excel

## Stack Tecnica

- Python 3.11+
- FastAPI
- SQLAlchemy 2
- Pydantic v2 + pydantic-settings
- SQLite (dev) e PostgreSQL (prod via `DATABASE_URL`)
- Pytest
- Ruff + MyPy
- Alembic
- Docker

## Arquitetura

- `app/routes`: camada HTTP
- `app/services`: regras de negocio
- `app/models`: entidades SQLAlchemy
- `app/schemas`: contratos Pydantic
- `app/database`: sessao, engine, dependencias e scripts de migracao legada
- `app/core`: configuracao e tratamento global de erros
- `app/static`: frontend web

## Estrutura (resumo)

```text
app/
  core/
  database/
  models/
  routes/
  schemas/
  services/
  static/
alembic/
tests/
main.py
pyproject.toml
```

## Configuracao de Ambiente

Copie `.env.example` para `.env.local` e ajuste:

```env
AUTOGESTOR_APP_ENV=development
DATABASE_URL=sqlite:///autogestor.db
AUTOGESTOR_SECRET_KEY=troque-esta-chave-por-um-segredo-forte
AUTOGESTOR_ACCESS_TOKEN_EXPIRE_MINUTES=10080
AUTOGESTOR_CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
```

## Instalacao e Execucao Local

```powershell
uv sync --dev
uv run alembic upgrade head
uv run uvicorn main:app --reload
```

API e frontend:

- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Frontend: `http://127.0.0.1:8000/static/login.html`
- Healthcheck: `http://127.0.0.1:8000/health`

## Banco e Migracoes

### Banco novo

```powershell
uv run alembic upgrade head
```

### Banco legado com dados

1. Execute migracao legada segura (gera backup automatico):

```powershell
uv run python app/database/migrar_espacos.py
```

2. Marque o estado atual para Alembic sem recriar tabelas:

```powershell
uv run alembic stamp head
```

## Qualidade e Testes

```powershell
uv run ruff check .
uv run mypy app/core
uv run pytest -q
```

## Docker

Build:

```powershell
docker build -t autogestor:latest .
```

Run:

```powershell
docker run --rm -p 8000:8000 --env-file .env.local autogestor:latest
```

## CI

Pipeline em `.github/workflows/ci.yml` com:

- `ruff check`
- `mypy`
- `pytest`

## Seguranca

- Senhas com hash bcrypt
- JWT com expiracao configuravel
- Segredo JWT via variavel de ambiente
- CORS configuravel por ambiente
- Rotas financeiras protegidas
- Isolamento por espaco financeiro
- Tratamento global de erros sem exposicao de stack trace

## Exemplos de Endpoints

- `POST /auth/cadastro`
- `POST /auth/login`
- `GET /auth/me`
- `GET /espacos`
- `GET /espacos/{espaco_id}/movimentacoes/?tipo=GASTO&data_inicio=2026-08-01&data_fim=2026-08-31&ordenar_por=valor&ordem=desc&limite=20&offset=0`
- `GET /espacos/{espaco_id}/movimentacoes/resumo-por-categoria`
- `GET /espacos/{espaco_id}/dashboard/resumo`

## Capturas de Tela

Adicione imagens em uma pasta `docs/images` e referencie aqui:

- `docs/images/login.png`
- `docs/images/dashboard.png`
- `docs/images/filtros.png`

## Proximos Passos

- Persistir metas financeiras no backend (hoje estao no localStorage)
- Adicionar endpoint de refresh token
- Evoluir cobertura de testes E2E no frontend
```

Interface: `http://127.0.0.1:8000/static/login.html`

Swagger: `http://127.0.0.1:8000/docs`

### Testes

```powershell
uv sync --all-groups
uv run pytest -q
```

Os testes usam SQLite em memória e não alteram `autogestor.db`.
