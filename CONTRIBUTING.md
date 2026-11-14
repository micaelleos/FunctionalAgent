# Como contribuir

Leia antes: [Constituição](.specify/memory/constitution.md) e
[processo de desenvolvimento](docs/modernizacao/08-processo-de-desenvolvimento.md).

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `backend/` | API FastAPI (Python 3.12, uv) |
| `frontend/` | SPA React + TypeScript + Vite |
| `infra/` | Infraestrutura (Terraform, a partir da F02) e emuladores Firebase |
| `legacy/` | App Streamlit antigo, mantido até o go-live (F12) |
| `scripts/` | Utilitários do repositório (ex.: rastreabilidade de requisitos) |
| `specs/` | Roadmap e uma pasta por feature (`spec.md`, `plan.md`, `tasks.md`) — formato Spec Kit |
| `docs/modernizacao/` | Plano de modernização: diagnóstico, arquitetura, stack, infra, CI/CD, ADRs |

## Pré-requisitos

- [uv](https://docs.astral.sh/uv/) 0.11+, Node 22, Docker, `make` (no Windows, use WSL ou Git Bash).

## Comandos

```bash
make install   # dependências de back e front
make dev       # emuladores + backend + frontend → http://localhost:5173
make lint      # ruff, mypy, import-linter, eslint, prettier, tsc
make test      # testes com cobertura mínima
make trace     # todo requisito tem teste?
make legacy    # Streamlit antigo
```

Sem Docker, rode as partes separadamente:

```bash
cd backend && uv run uvicorn app.main:app --reload    # http://localhost:8000/healthz
cd frontend && npm run dev                            # http://localhost:5173
```

## Fluxo de trabalho

1. A feature precisa de spec e plano aprovados em `specs/0xx-slug/` (Gate 0 e Gate 1).
   Índice e status: [`specs/ROADMAP.md`](specs/ROADMAP.md). Nova feature: `/speckit-specify`.
2. Crie um branch `feat/Fxx-descricao` a partir de `master`.
3. Marque os testes com o ID do requisito:
   - pytest: `@pytest.mark.req("F05-RF-01")`
   - Vitest/Playwright: inclua o ID no `describe`/`test`, ex.: `describe('F08-RF-01 ...')`
4. Abra o PR usando o template (checklist da Constituição). O CI precisa estar verde.

## Regras de camadas do backend

`api → services → agent | integrations | repositories → core`, verificadas pelo `import-linter`.
