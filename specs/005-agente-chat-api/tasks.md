# F05 — API de chat com agente (Gemini + streaming) — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 10 tarefas · 12,5 d. Revisão 2026-11-16: T008 e T009 (specs para agentes de código, ADR-007); T010 e T004 com Gemini no Vertex AI (ADR-008).
**Dividir antes de implementar** (> 1 d, Art. I/VI): T001 (1,5 d), T003 (2 d), T004 (1,5 d), T005 (1,5 d), T007 (1,5 d).

## 8. Tarefas

### Fase 1: Preparação

**Objetivo:** Gravar o baseline do agente legado **antes** da migração (risco do roadmap).

- [ ] T001 Dataset inicial de evals (30 casos) + baseline do agente legado — teste: `evals/` — 1,5 d

---

### Fase 2: Fundação

**Objetivo:** Conversão de descrições para o formato do Jira v3.

- [ ] T002 Conversor Markdown→ADF — teste: unit com fixtures — 1 d
- [ ] T008 [F05-RF-06] `AgentReadySpec` + renderizador ADF/Markdown com seções fixas (F05-RT-13) — teste: `test_agent_ready_spec.py` com fixtures — 1 d
- [ ] T009 [P] [F05-RF-06][F05-RF-11] Verificação de prontidão P-01..P-10 e labels (F05-RT-14, F05-RT-15) — teste: `test_readiness.py` — 1 d
- [ ] T010 [P] Vertex AI no Terraform (API, papel da SA, `LLM_MODEL`/`LLM_LOCATION`; remove `specflow-llm-api-key`) + `GeminiModelClient` e config (F05-RT-09) — teste: `make infra-check`, unit de config, chamada real ao modelo no smoke — 0,5 d

---

### Fase 3: Incremento 1 — ferramentas do agente

**Objetivo:** Leitura do Jira e propostas de ação sem escrita.

**Aceitação:** AT-F05-03, AT-F05-04, AT-F05-05

- [ ] T003 [F05-RF-03][F05-RF-04][F05-RF-05] Ferramentas de leitura e de proposta (com `pending_actions`) — teste: unit com `JiraClient` fake — 2 d

---

### Fase 4: Incremento 2 — conversa em streaming

**Objetivo:** Agente isolado por usuário/conversa, respondendo em SSE.

**Aceitação:** AT-F05-01, AT-F05-02, AT-F05-06

- [ ] T004 [F05-RF-02][F05-RF-06][F05-RF-08][F05-RF-09][F05-RF-10][F05-RF-11][F05-RF-12] Loop do agente (`agent/loop.py`, `ModelClient`) + prompt v1 (perguntar antes de inventar, dividir, `human-only`, avaliar issue existente) — teste: integração com `ScriptedModelClient` — 1,5 d
- [ ] T005 [F05-RF-02] Serviço de chat: histórico, janela/sumarização, persistência, uso — teste: integração com emulador — 1,5 d
- [ ] T006 [F05-RF-01][F05-RF-07] Endpoint SSE + esquema de eventos + contrato — teste: contrato — 1 d

---

### Fase 5: Validação e entrega

**Objetivo:** Aceitação em dev e evals não piores que o baseline.

**Aceitação:** AT-F05-01..09

- [ ] T007 Testes de aceitação AT-F05-01..09 + evals comparadas ao baseline — teste: acceptance + evals — 1,5 d
