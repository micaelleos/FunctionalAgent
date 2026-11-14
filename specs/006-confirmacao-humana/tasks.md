# F06 — Confirmação humana antes de escrever no Jira — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 5 tarefas · 5 d.
**Dividir antes de implementar** (> 1 d, Art. I/VI): T001 (1,5 d).

## 8. Tarefas

### Fase 1: Fundação

**Objetivo:** Ciclo de vida seguro das ações propostas.

**Aceitação:** AT-F06-04

- [ ] T001 Máquina de estados + transação + hash do payload — teste: unit + concorrência — 1,5 d

---

### Fase 2: Incremento 1 — confirmar e recusar no backend

**Objetivo:** Execução exata do que foi confirmado; recusa, expiração e erros traduzidos.

**Aceitação:** AT-F06-01, AT-F06-02, AT-F06-06

- [ ] T002 [F06-RF-02][F06-RF-03][F06-RF-05][F06-RF-07] Endpoints confirm/reject/list + tradução de erros — teste: integração — 1 d
- [ ] T003 [F06-RF-02][F06-RF-03] Mensagem de sistema + registro em `jira_issues` — teste: integração — 0,5 d

---

### Fase 3: Incremento 2 — cartão de ação

**Objetivo:** Cartão com a prévia completa e antes/depois.

**Aceitação:** AT-F06-01, AT-F06-05

- [ ] T004 [P] [F06-RF-01][F06-RF-06] `<ActionCard>` + diff antes/depois — teste: Vitest — 1 d

---

### Fase 4: Validação e entrega

**Objetivo:** Cenários de aceitação automatizados.

**Aceitação:** AT-F06-01..06

- [ ] T005 AT-F06-01..06 — teste: Playwright/API — 1 d
