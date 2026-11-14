# F05 — API de chat com agente (LangGraph + streaming) — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 7 tarefas · 10 d.
**Dividir antes de implementar** (> 1 d, Art. I/VI): T001 (1,5 d), T003 (2 d), T004 (1,5 d), T005 (1,5 d), T007 (1,5 d).

## 8. Tarefas

### Fase 1: Preparação

**Objetivo:** Gravar o baseline do agente legado **antes** da migração (risco do roadmap).

- [ ] T001 Dataset inicial de evals (30 casos) + baseline do agente legado — teste: `evals/` — 1,5 d

---

### Fase 2: Fundação

**Objetivo:** Conversão de descrições para o formato do Jira v3.

- [ ] T002 Conversor Markdown→ADF — teste: unit com fixtures — 1 d

---

### Fase 3: Incremento 1 — ferramentas do agente

**Objetivo:** Leitura do Jira e propostas de ação sem escrita.

**Aceitação:** AT-F05-03, AT-F05-04, AT-F05-05

- [ ] T003 [F05-RF-03][F05-RF-04][F05-RF-05] Ferramentas de leitura e de proposta (com `pending_actions`) — teste: unit com `JiraClient` fake — 2 d

---

### Fase 4: Incremento 2 — conversa em streaming

**Objetivo:** Agente isolado por usuário/conversa, respondendo em SSE.

**Aceitação:** AT-F05-01, AT-F05-02, AT-F05-06

- [ ] T004 [F05-RF-02][F05-RF-06][F05-RF-08] Grafo LangGraph + prompt v1 + config de modelo — teste: integração com LLM scripted — 1,5 d
- [ ] T005 [F05-RF-02] Serviço de chat: histórico, janela/sumarização, persistência, uso — teste: integração com emulador — 1,5 d
- [ ] T006 [F05-RF-01][F05-RF-07] Endpoint SSE + esquema de eventos + contrato — teste: contrato — 1 d

---

### Fase 5: Validação e entrega

**Objetivo:** Aceitação em dev e evals não piores que o baseline.

**Aceitação:** AT-F05-01..06

- [ ] T007 Testes de aceitação AT-F05-01..06 + evals comparadas ao baseline — teste: acceptance + evals — 1,5 d
