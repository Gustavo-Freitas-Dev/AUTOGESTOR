# 🚀 AutoGestor

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-REST_API-green)
![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-orange)
![License](https://img.shields.io/badge/License-MIT-purple)

API REST desenvolvida com **FastAPI** para gerenciamento financeiro pessoal, permitindo o cadastro de ganhos e gastos, além da geração de relatórios financeiros.

---

## 📖 Sobre o Projeto

O **AutoGestor** nasceu com o objetivo de aplicar boas práticas de desenvolvimento backend utilizando Python e FastAPI.

A aplicação permite o gerenciamento de informações financeiras por meio de uma API organizada em camadas, facilitando manutenção, escalabilidade e futuras integrações com bancos de dados e sistemas externos.

### Funcionalidades

* ✅ Cadastro de ganhos
* ✅ Cadastro de gastos
* ✅ Consulta de relatórios financeiros
* ✅ Organização de despesas por categoria
* ✅ Documentação automática com Swagger e ReDoc
* 🚧 Persistência em banco de dados (em desenvolvimento)

---

## 🛠️ Tecnologias Utilizadas

* Python 3.11+
* FastAPI
* Pydantic
* Uvicorn
* UV (Gerenciamento de dependências)

---

## 📁 Estrutura do Projeto

```text
AutoGestor/
│
├── app/
│   ├── routes/
│   │   ├── ganhos.py
│   │   ├── gastos.py
│   │   └── relatorio.py
│   │
│   ├── services/
│   │   └── gastos_service.py
│   │
│   ├── schemas/
│   │   └── gastos_schema.py
│   │
│   └── static/
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

### Windows

```powershell
.\.venv\Scripts\Activate.ps1
```

### Linux/macOS

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

---

## 📚 Documentação

### Swagger UI

```text
http://127.0.0.1:8000/docs
```

### ReDoc

```text
http://127.0.0.1:8000/redoc
```

---

## 🔗 Endpoints

### Sistema

| Método | Endpoint | Descrição                     |
| ------ | -------- | ----------------------------- |
| GET    | /        | Verifica se a API está online |

### Gastos

| Método | Endpoint | Descrição                   |
| ------ | -------- | --------------------------- |
| POST   | /gastos  | Cadastra um novo gasto      |
| GET    | /gastos  | Lista os gastos cadastrados |

### Ganhos

| Método | Endpoint | Descrição                   |
| ------ | -------- | --------------------------- |
| POST   | /ganhos  | Cadastra um novo ganho      |
| GET    | /ganhos  | Lista os ganhos cadastrados |

### Relatórios

| Método | Endpoint    | Descrição                        |
| ------ | ----------- | -------------------------------- |
| GET    | /relatorios | Retorna informações consolidadas |

---

## 📦 Exemplo de Requisição

### POST /gastos

```json
{
  "categoria": "alimentacao",
  "descricao": "Mercado",
  "valor": 120.50
}
```

### Resposta

```json
{
  "id": 1,
  "categoria": "alimentacao",
  "descricao": "Mercado",
  "valor": 120.50
}
```

---

## 🎯 Objetivos de Aprendizado

Este projeto foi desenvolvido para aprofundar conhecimentos em:

* Desenvolvimento de APIs REST
* FastAPI
* Pydantic
* Arquitetura em camadas
* Boas práticas de desenvolvimento backend
* Organização de projetos Python

---

## 🚀 Roadmap

* [ ] Persistência com SQLite
* [ ] Integração com PostgreSQL
* [ ] SQLAlchemy ORM
* [ ] Alembic
* [ ] Autenticação JWT
* [ ] Docker
* [ ] Testes automatizados com Pytest
* [ ] Deploy em nuvem

---

## 👨‍💻 Autor

**Gustavo Freitas**

Desenvolvedor Python focado em Backend, automação de processos e desenvolvimento de APIs.

Linkedin: https://www.linkedin.com/in/gustavo-freitas-dev/
