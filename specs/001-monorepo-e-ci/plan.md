# F01 — Monorepo, tooling e CI base — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- Estrutura conforme `03-arquitetura.md §7`. `git mv` de `main.py`, `pages/`, `src/` para `legacy/`.
- Remover `src/scripts/llm_openai.py`, `src/scripts/tools.py`, `prompt_1`, todos os `__pycache__`.
- `Makefile` multiplataforma (ou `justfile`): `dev`, `test`, `lint`, `legacy`, `gen-client`.
- `ci.yml` com jobs `backend` e `frontend` filtrados por caminho (`dorny/paths-filter`).
- Branch protection em `master`: checks obrigatórios + 1 review.

### 9. Plano de testes
Unit: `test_healthz`, render da página de status. CI: o próprio pipeline é o teste (AT-F01-02 com PR de prova).
