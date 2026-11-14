# F03 — Autenticação e conta do usuário — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · formato do `tasks-template` do projeto (checklist lido por
`/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 7 tarefas · 6,5 d. Revisado em 2026-11-14 com as decisões do PO (Auth compartilhado).

## 8. Tarefas

### Fase 1: Fundação

**Objetivo:** Autorização genérica por token para todas as rotas.

**Aceitação:** AT-F03-03

- [ ] T001 [F03-RF-02] `core/auth.py`, `core/errors.py` (Problem Details), `api/deps.py::current_user` (403 sem e-mail verificado) — teste: `test_authz.py` (matriz rota × token) — 1 d

---

### Fase 2: Incremento 1 — conta no backend

**Objetivo:** Perfil criado no primeiro acesso; exportar e excluir dados.

**Aceitação:** AT-F03-02, AT-F03-04

- [ ] T002 [F03-RF-05] `repositories/users.py`, `services/account.py`, `GET /api/v1/me` (cria perfil) — teste: `test_me.py` no emulador — 1 d
- [ ] T003 [F03-RF-07][F03-RF-08] `GET /api/v1/me/export` e `DELETE /api/v1/me` (só dados do banco `specflow`, idempotente) — teste: `test_me.py`, `test_account_delete.py` (10 mil docs < 30 s) — 1 d

---

### Fase 3: Incremento 2 — login e conta na interface

**Objetivo:** Login Google/e-mail, rotas protegidas, página Conta.

**Aceitação:** AT-F03-01, AT-F03-02, AT-F03-04

- [ ] T004 [P] [F03-RF-04] SDK Firebase, `AuthProvider`, `react-router`, `<ProtectedRoute>`, cliente da API com token e retry em 401 — teste: Vitest + MSW — 1 d
- [ ] T005 [F03-RF-01][F03-RF-02][F03-RF-03] Telas `/login`, `/cadastro` (aviso de verificação), `/recuperar-senha` — teste: Vitest + MSW, axe — 1 d
- [ ] T006 [F03-RF-06][F03-RF-07][F03-RF-08] Página `/conta` (exportar, excluir com "EXCLUIR" e aviso do login compartilhado, sair) — teste: Vitest + MSW — 0,5 d

---

### Fase 4: Validação e entrega

**Objetivo:** Cenários de aceitação automatizados e publicação.

**Aceitação:** AT-F03-01..04

- [ ] T007 `make deploy-web` injeta a config do Firebase; E2E AT-F03-01..04 nos emuladores + job no CI; `make deploy` e roteiro manual M-F03-01/02 — teste: Playwright — 1 d
