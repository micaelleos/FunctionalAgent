# F10 — Histórico de issues criados — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 4 tarefas · 3,5 d. Revisão 2026-11-16: T004 (copiar para agente, ADR-007).

## 8. Tarefas

### Fase 1: Incremento 1 — histórico de issues

**Objetivo:** Histórico persistente, filtrável, com links e status sob demanda.

**Aceitação:** AT-F10-01..03

- [ ] T001 [F10-RF-01][F10-RF-02][F10-RF-03] Endpoint + índices + filtros — teste: integração/contrato — 1 d
- [ ] T002 [P] [F10-RF-03][F10-RF-04][F10-RF-05] Página + filtros + status sob demanda — teste: Vitest — 1 d

---

### Fase 2: Validação e entrega

**Objetivo:** Cenários de aceitação automatizados.

**Aceitação:** AT-F10-01..03

- [ ] T004 [P] [F10-RF-06][F10-RF-07] "Copiar para agente de código" + marca/filtro de prontidão — teste: Vitest — 0,5 d
- [ ] T003 AT-F10-01..04 — teste: Playwright — 1 d
