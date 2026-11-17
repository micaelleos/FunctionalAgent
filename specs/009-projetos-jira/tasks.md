# F09 — Projetos Jira — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 5 tarefas · 3 d. Revisado em 2026-11-17 (T001 dividida em T001/T004; T005 novo).

## 8. Tarefas

### Fase 1: Incremento 1 — projetos Jira

**Objetivo:** Listar, contar, filtrar e agir sobre projetos.

**Aceitação:** AT-F09-01..03

- [ ] T001 [F09-RF-01][F09-RF-04] Cliente: paginação de `project/search` com `insight` e `approximate_count` — teste: `test_jira_client.py` — 0,5 d
- [ ] T004 [F09-RF-02][F09-RF-06][F09-RF-07] Serviço + cache no Firestore + `GET /api/v1/jira/projects` — teste: `test_jira_projects.py` — 1 d
- [ ] T002 [P] [F09-RF-03][F09-RF-04][F09-RF-05][F09-RF-06] Página ligada à API: avatar, "—", filtro, ações, "Refresh", erro de credencial — teste: `ProjectsPage.test.tsx`, `http.test.ts` — 0,5 d

---

### Fase 2: Validação e entrega

**Objetivo:** Cenários de aceitação automatizados.

**Aceitação:** AT-F09-01..03

- [ ] T005 [P] p95 com Jira falso (F09-RT-06) — teste: `test_jira_projects_perf.py` — 0,25 d
- [ ] T003 AT-F09-01..03 — teste: `e2e/f09-projetos.spec.ts` — 0,75 d
