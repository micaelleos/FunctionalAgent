# F01 — Monorepo, tooling e CI base — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

> Cada tarefa ≤ 1 dia e acompanhada do seu teste (Constituição, Art. I e VI).

### 8. Tarefas
| # | Tarefa | Teste | Est. |
|---|---|---|---|
| 1 | Mover legado, limpar código morto e pyc, `.gitignore` | AT-F01-03 | 0,5 d |
| 2 | `backend/` com uv, FastAPI, `/healthz`, ruff/mypy/import-linter, pytest | `test_healthz` | 1 d |
| 3 | `frontend/` com Vite/React/TS, Tailwind, Vitest, ESLint; página de status | `App.test.tsx` | 1 d |
| 4 | Dockerfile backend + `docker-compose` com emuladores Firebase | AT-F01-01 | 1 d |
| 5 | `ci.yml`, template de PR, pre-commit, branch protection | AT-F01-02 | 1 d |
| 6 | `scripts/trace_requirements.py` + README de contribuição | teste do script | 0,5 d |
