# QA Test Manager

Aplicação web local para gerir projetos, casos de teste, execuções e incidências, com colaboração humana assistida pela agente QA Eva através do ChatGPT/Codex.

## Estado

Release 1 em desenvolvimento, com modelo de dados, autenticação local e gestão de projetos e utilizadores. Ainda não existem casos de teste ou integração da Eva.

## Arquitetura

- `apps/web`: React, TypeScript e Vite.
- `apps/api`: FastAPI e Python.
- `docs`: decisões arquiteturais e documentação do produto.
- `work/eva`: futura pasta local de troca com a Eva; ignorada pelo Git.

## Requisitos locais

- Node.js 22 ou superior.
- pnpm 10 ou superior.
- Python 3.12 ou superior.

## Preparação

```bash
pnpm install
python -m venv .venv
```

Ative o ambiente virtual e instale o backend:

```bash
python -m pip install -e "apps/api[dev]"
```

## Executar

API:

```bash
python -m uvicorn qa_test_manager.main:app --app-dir apps/api/src --reload
```

Web, noutro terminal:

```bash
pnpm dev:web
```

- Web: `http://localhost:5173`
- API: `http://localhost:8000`
- Health check: `http://localhost:8000/health`

Na primeira utilização, aplique as migrações e crie o utilizador local chamado `Admin`. Informe o email de login e defina a palavra-passe de forma interativa; ela nunca fica no código:

```bash
cd apps/api
python -m alembic upgrade head
python -m qa_test_manager.bootstrap_admin
```

## Verificações

```bash
pnpm check
python -m pytest apps/api/tests
python -m ruff check apps/api
python -m mypy apps/api/src
cd apps/api && python -m alembic upgrade head
```

## Privacidade

A aplicação é executada localmente. O GitHub é apenas um espelho público do código. Bases de dados, uploads, evidências, credenciais e ficheiros de troca com a Eva não devem ser versionados.

## Documentação

- [Arquitetura](docs/architecture.md)
- [ADR 0001 — Monorepo](docs/adr/0001-monorepo.md)
- [ADR 0002 — Autenticação local](docs/adr/0002-local-authentication.md)
- [ADR 0003 — Colaboração com a Eva](docs/adr/0003-eva-file-collaboration.md)
