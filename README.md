# QA Test Manager

Aplicação web local para gerir projetos, casos de teste, execuções e incidências, com colaboração humana assistida pela agente QA Eva através do ChatGPT/Codex.

## Estado

Release 1 em desenvolvimento, com modelo de dados, autenticação local, gestão de projetos, utilizadores, casos de teste manuais e exportação em DOCX, XLSX e PDF. A integração da Eva ainda não existe.

As exportações podem abranger um caso individual ou a lista filtrada do projeto. Os ficheiros são gerados em memória e descarregados pelo browser; não são guardados no repositório nem na base de dados.

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

Os fluxos críticos por perfil usam Playwright. Instale o browser uma vez e execute:

```bash
pnpm test:e2e:install
pnpm test:e2e
```

O E2E cria somente `apps/api/e2e-release1-demo.db`, ignorada pelo Git.

## Dados de demonstração

O seed é opcional, usa dados fictícios e recusa a base normal. Defina uma base com `demo` no nome, uma senha exclusiva e a autorização explícita:

```powershell
$env:QA_TEST_MANAGER_DATABASE_URL = "sqlite:///./demo-portfolio.db"
$env:QA_TEST_MANAGER_ALLOW_DEMO_SEED = "1"
$env:QA_TEST_MANAGER_DEMO_PASSWORD = "defina-uma-senha-com-12-caracteres"
cd apps/api
python -m alembic upgrade head
python -m qa_test_manager.seed_demo
```

São criados Admin, Tester e Dev fictícios, um projeto e um caso manual. Nunca use este seed numa base com dados reais.

## Roteiro de demonstração

1. Entrar como Admin, criar um projeto e abrir a gestão de utilizadores.
2. Criar ou editar um caso manual e confirmar a numeração `CT001` por projeto.
3. Aplicar filtros e exportar a lista em DOCX, XLSX e PDF.
4. Entrar como Tester e confirmar a criação de casos no projeto atribuído.
5. Entrar como Dev e confirmar o acesso somente de leitura.
6. Mostrar a auditoria e os testes automatizados no repositório.

## Privacidade

A aplicação é executada localmente. O GitHub é apenas um espelho público do código. Bases de dados, uploads, evidências, credenciais e ficheiros de troca com a Eva não devem ser versionados.

## Documentação

- [Arquitetura](docs/architecture.md)
- [ADR 0001 — Monorepo](docs/adr/0001-monorepo.md)
- [ADR 0002 — Autenticação local](docs/adr/0002-local-authentication.md)
- [ADR 0003 — Colaboração com a Eva](docs/adr/0003-eva-file-collaboration.md)
- [Modelo de ameaças](docs/threat-model.md)
