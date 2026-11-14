# F01 — Monorepo, tooling e CI base — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 6 tarefas · 5 d.

## 8. Tarefas

### Fase 1: Preparação

**Objetivo:** Separar o app legado e limpar o repositório.

**Aceitação:** AT-F01-03

- [X] T001 [F01-RF-05] Mover legado para `legacy/`, limpar código morto e pyc, `.gitignore` — teste: AT-F01-03 — 0,5 d

---

### Fase 2: Incremento 1 — app local de ponta a ponta

**Objetivo:** Front, back e emuladores sobem juntos e o front exibe o `/healthz`.

**Aceitação:** AT-F01-01

- [X] T002 [F01-RF-02] `backend/` com uv, FastAPI, `/healthz`, ruff/mypy/import-linter, pytest — teste: `backend/tests/unit/test_health.py` — 1 d
- [X] T003 [P] [F01-RF-03] `frontend/` com Vite/React/TS, Tailwind, Vitest, ESLint; página de status — teste: `frontend/src/App.test.tsx` — 1 d
- [X] T004 [F01-RF-01] Dockerfile do backend + `docker-compose.yml` com emuladores Firebase — teste: AT-F01-01 — 1 d

---

### Fase 3: Incremento 2 — qualidade automatizada

**Objetivo:** Todo PR roda lint, tipos, testes e build; requisitos rastreáveis.

**Aceitação:** AT-F01-02

- [ ] T005 [F01-RF-04] `ci.yml`, template de PR, pre-commit, branch protection (feitos: ci.yml, template, pre-commit; pendente: confirmar branch protection em `master`) — teste: AT-F01-02 — 1 d
- [X] T006 `scripts/trace_requirements.py` + `CONTRIBUTING.md` — teste: `scripts/test_trace_requirements.py` — 0,5 d
