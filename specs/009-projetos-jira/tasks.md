# F09 — Projetos Jira — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 3 tarefas · 3 d.

## 8. Tarefas

### Fase 1: Incremento 1 — projetos Jira

**Objetivo:** Listar, contar, filtrar e agir sobre projetos.

**Aceitação:** AT-F09-01..03

- [ ] T001 [F09-RF-01][F09-RF-02] Endpoint + paginação + contagem paralela + cache — teste: unit/integração — 1 d
- [ ] T002 [P] [F09-RF-03][F09-RF-04][F09-RF-05][F09-RF-06] Página com filtro e ações — teste: Vitest — 1 d

---

### Fase 2: Validação e entrega

**Objetivo:** Cenários de aceitação automatizados.

**Aceitação:** AT-F09-01..03

- [ ] T003 AT-F09-01..03 — teste: Playwright — 1 d
