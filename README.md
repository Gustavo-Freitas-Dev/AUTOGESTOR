# 💼 AutoGestor

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-REST_API-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-red?logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-orange)
![License](https://img.shields.io/badge/License-MIT-purple)

API REST desenvolvida com **FastAPI** para gerenciamento financeiro pessoal — controle de **ganhos e gastos** em uma estrutura unificada de movimentações, com persistência em banco de dados via **SQLAlchemy** e dashboard de indicadores consolidados.

Inclui também um **frontend standalone em HTML/CSS/JS** (sem frameworks), com dashboard interativo, gráficos, metas por categoria, exportação de relatórios e modais de confirmação — pensado para consumir essa API diretamente.

---

## 📖 Sobre o Projeto

O **AutoGestor** nasceu como um projeto de estudo para aplicar boas práticas de desenvolvimento backend com Python, evoluindo de uma estrutura inicial com rotas separadas (`/ganhos`, `/gastos`) para um modelo mais robusto e escalável: um **único recurso de movimentações financeiras**, diferenciadas por um campo `tipo` (`GANHO` ou `GASTO`).

Essa decisão de arquitetura simplifica consultas consolidadas (saldo, relatórios, dashboards) e reflete um padrão mais próximo do que se vê em sistemas financeiros reais, onde receitas e despesas compartilham os mesmos atributos estruturais (categoria, valor, data, descrição) e se diferenciam apenas pela natureza da operação.

### Funcionalidades

* ✅ Cadastro de movimentações (ganhos e gastos) em um único endpoint
* ✅ Atualização e exclusão de movimentações
* ✅ Busca de movimentação por ID
* ✅ Listagem completa com filtros aplicáveis no frontend
* ✅ Dashboard com indicadores consolidados
* ✅ Persistência em banco de dados com SQLAlchemy
* ✅ Documentação automática com Swagger e ReDoc
* ✅ Frontend completo (HTML/CSS/JS) com gráficos, metas e exportação CSV/Excel
* 🚧 Autenticação e múltiplos usuários (planejado)

---

## 🛠️ Tecnologias Utilizadas

**Backend**
* Python 3.11+
* FastAPI
* Pydantic — validação e schemas
* SQLAlchemy — ORM
* Uvicorn — servidor ASGI
* UV — gerenciamento de dependências

**Frontend**
* HTML5, CSS3 e JavaScript puro (sem frameworks ou build tools)
* SheetJS (via CDN) — exportação para Excel

---

## 📁 Estrutura do Projeto

```text
AutoGestor/
│
├── app/
│   ├── database/
│   │   ├── base.py          # Base declarativa do SQLAlchemy
│   │   ├── db.py             # Engine e configuração de conexão
│   │   └── dependencies.py   # Dependency injection (get_db)
│   │
│   ├── models/
│   │   └── movimentacao_model.py
│   │
│   ├── routes/
│   │   ├── movimentacoes.py  # CRUD de movimentações
│   │   └── dashboard.py      # Indicadores consolidados
│   │
│   ├── schemas/
│   │   └── movimentacao_schemas.py   # CriarMovimentacao, AtualizarMovimentacao
│   │
│   ├── services/
│   │   └── movimentacao_service.py   # Regras de negócio
│   │
│   └── static/
│       └── autogestor.html   # Frontend standalone
│
├── main.py
├── pyproject.toml
└── README.md
```

---

## ⚙️ Instalação

Clone o repositório:

```bash
git clone https://github.com/SEU-USUARIO/autogestor.git
```

Acesse o diretório:

```bash
cd autogestor
```

Crie o ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente:

**Windows**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS**
```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
uv sync
```

---

## ▶️ Executando a Aplicação

```bash
uvicorn main:app --reload
```

A API ficará disponível em:

```text
http://127.0.0.1:8000
```

O frontend (`autogestor.html`) pode ser aberto diretamente no navegador ou servido como arquivo estático pela própria API.

> **Nota:** se o frontend for aberto como arquivo local (`file://`) ou servido em uma porta diferente da API, é necessário habilitar **CORS** no `main.py` para que as requisições não sejam bloqueadas pelo navegador. Veja a seção [CORS](#-cors) abaixo.

---

## 📚 Documentação Interativa

| Ferramenta | URL |
|---|---|
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |

---

## 🔗 Endpoints

### Sistema

| Método | Endpoint | Descrição |
| ------ | -------- | --------- |
| GET    | `/` | Verifica se a API está online |

### Movimentações

| Método | Endpoint | Descrição |
| ------ | -------- | --------- |
| POST   | `/movimentacoes/` | Cadastra uma nova movimentação (ganho ou gasto) |
| GET    | `/movimentacoes/` | Lista todas as movimentações cadastradas |
| GET    | `/movimentacoes/{id}` | Busca uma movimentação específica pelo ID |
| PUT    | `/movimentacoes/{id}` | Atualiza uma movimentação existente |
| DELETE | `/movimentacoes/{id}` | Remove uma movimentação |

### Dashboard

| Método | Endpoint | Descrição |
| ------ | -------- | --------- |
| GET    | `/dashboard` | Retorna indicadores financeiros consolidados |

---

## 📦 Exemplo de Requisição

### POST `/movimentacoes/`

```json
{
  "tipo": "GASTO",
  "categoria": "Alimentação",
  "descricao": "Mercado",
  "valor": 120.50,
  "data": "2026-06-29"
}
```

### Resposta

```json
{
  "id": 1,
  "tipo": "GASTO",
  "categoria": "Alimentação",
  "descricao": "Mercado",
  "valor": 120.50,
  "data": "2026-06-29"
}
```

### POST `/movimentacoes/` (ganho)

```json
{
  "tipo": "GANHO",
  "categoria": "Freelance",
  "descricao": "Projeto landing page",
  "valor": 850.00,
  "data": "2026-06-28"
}
```

---

## 🌐 CORS

Caso o frontend seja consumido de uma origem diferente da API (arquivo local, Live Server, outra porta), é necessário adicionar o middleware de CORS no `main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # em produção, restrinja à URL real do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Sem essa configuração, o navegador bloqueia silenciosamente as requisições do frontend para a API — sintoma comum: formulário parece "salvar" mas nada aparece no banco.

---

## 🖥️ Frontend

O projeto inclui um dashboard financeiro completo, construído com HTML, CSS e JavaScript puro — sem dependência de frameworks ou processo de build:

* Cadastro de movimentações com seletor de tipo (Ganho/Gasto)
* Cards de saldo (entradas, saídas, saldo líquido)
* Filtros por tipo e por período (hoje, 7 dias, mês atual, intervalo customizado)
* Gráfico de gastos por categoria
* Gráfico de evolução do saldo ao longo do tempo
* Metas de gasto mensal por categoria, com barra de progresso
* Edição e exclusão com modais de confirmação
* Exportação de relatórios em **CSV** e **Excel**
* Notificações toast para feedback de ações
* Skeleton loading durante o carregamento dos dados

---

## 🎯 Objetivos de Aprendizado

Este projeto foi desenvolvido para aprofundar conhecimentos em:

* Desenvolvimento de APIs REST com FastAPI
* Modelagem de dados e validação com Pydantic
* Persistência de dados com SQLAlchemy
* Arquitetura em camadas (routes → services → schemas → models)
* Boas práticas de organização de projetos Python
* Integração entre frontend e backend via fetch/REST
* Construção de interfaces ricas sem frameworks JavaScript

---

## 🚀 Roadmap

* [x] Persistência com banco de dados (SQLAlchemy)
* [x] Endpoint de dashboard consolidado
* [x] Frontend completo com gráficos e exportação
* [ ] Filtros e relatórios diretamente na API (por período, categoria)
* [x] Autenticação JWT e múltiplos usuários
* [x] Espaços financeiros pessoais e compartilhados
* [ ] Endpoint dedicado para metas de gasto (atualmente local no frontend)
* [ ] Migrations com Alembic
* [x] Testes automatizados com Pytest
* [ ] Containerização com Docker
* [ ] Deploy em nuvem

---

## 👨‍💻 Autor

**Gustavo Freitas**

Desenvolvedor Python focado em Backend, automação de processos e desenvolvimento de APIs.

[LinkedIn](https://www.linkedin.com/in/gustavo-freitas-dev/)

---

## Espaços financeiros

Cada conta recebe automaticamente um espaço pessoal. Usuários autenticados também podem criar espaços compartilhados, convidar outra pessoa por um código seguro de oito caracteres e alternar o espaço ativo pelo cabeçalho.

Todas as movimentações e cálculos do dashboard são isolados pelo espaço selecionado. A API valida a associação do usuário antes de listar, criar, editar ou excluir dados.

### Atualização de um banco existente

Pare o servidor e execute uma única vez:

```powershell
uv run python app/database/migrar_espacos.py
```

O comando cria automaticamente um arquivo `autogestor.backup_DATA_HORA.db` antes da migração. Ele preserva usuários e associa cada movimentação antiga ao espaço pessoal de seu proprietário.

Não use `corrigir_banco.py` depois dessa migração, pois esse script pertence ao modelo antigo baseado em `usuario_id`.

### Execução

Configure uma chave JWT permanente e inicie a aplicação:

```powershell
$env:AUTOGESTOR_SECRET_KEY="uma-chave-longa-e-aleatoria"
uv run uvicorn main:app --reload
```

Interface: `http://127.0.0.1:8000/static/login.html`

Swagger: `http://127.0.0.1:8000/docs`

### Testes

```powershell
uv sync --all-groups
uv run pytest -q
```

Os testes usam SQLite em memória e não alteram `autogestor.db`.
