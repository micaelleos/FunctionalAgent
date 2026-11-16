# F05 — API de chat com agente (LangGraph + Gemini + streaming) — Tarefas

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

- [x] T001 Dataset inicial de evals (30 casos) + baseline do agente legado — teste: `evals/` — 1,5 d
  - [x] T001a Dataset `evals/datasets/f05_v1.jsonl` (30 casos) e runner com métricas determinísticas — 1 d
  - [x] T001b Baseline gravado: `prompt_2` + ferramentas legadas no mesmo Gemini (o GPT do legado não tem chave; ver `evals/README.md`) — precisa do Vertex AI ativo — 0,5 d

---

### Fase 2: Fundação

**Objetivo:** Conversão de descrições para o formato do Jira v3.

- [x] T002 Conversor Markdown⇄ADF (`agent/spec/adf.py`; o renderizador usa o Markdown inline) — teste: `test_adf.py` — 1 d
- [x] T008 [F05-RF-06] `AgentReadySpec` + renderizador ADF/Markdown com seções fixas (F05-RT-13) — teste: `test_agent_ready_spec.py` com fixtures — 1 d
- [x] T009 [P] [F05-RF-06][F05-RF-11] Verificação de prontidão P-01..P-10 e labels (F05-RT-14, F05-RT-15) — teste: `test_readiness.py` — 1 d
- [x] T010 [P] Vertex AI no Terraform (API, papel da SA, `LLM_MODEL`/`LLM_LOCATION`; remove `specflow-llm-api-key`) + fábrica `build_chat_model` e config (F05-RT-09) — teste: `make infra-check`, unit de config, chamada real ao modelo no smoke — 0,5 d
  - [x] T010a Terraform (API, papel, envs, segredo removido), fábrica, config e smoke no `deploy.sh` — teste: `terraform validate`, `test_llm_config.py` — 0,4 d
  - [x] T010b `terraform apply` aprovado pelo PO e smoke do modelo em produção — 0,1 d

---

### Fase 3: Incremento 1 — ferramentas do agente

**Objetivo:** Leitura do Jira e propostas de ação sem escrita.

**Aceitação:** AT-F05-03, AT-F05-04, AT-F05-05

- [x] T003 [F05-RF-03][F05-RF-04][F05-RF-05] Ferramentas de leitura e de proposta (com `pending_actions`) — teste: unit com `JiraClient` fake — 2 d
  - [x] T003a Leitura no `JiraClient` (projetos, issue, JQL ≤ 50) + adaptador de erros — teste: `test_jira_read.py` — 0,5 d
  - [x] T003b Ferramentas de leitura com dado não confiável e truncamento — teste: `test_tools_read.py` — 0,5 d
  - [x] T003c Propostas (história/tarefa, épico, atualização) e campos do Jira (RT-06) — teste: `test_tools_propose.py` — 0,5 d
  - [x] T003d `avaliar_prontidao` com leitor de issue existente (F05-RF-12) — teste: `test_readiness_review.py` — 0,5 d

---

### Fase 4: Incremento 2 — conversa em streaming

**Objetivo:** Agente isolado por usuário/conversa, respondendo em SSE.

**Aceitação:** AT-F05-01, AT-F05-02, AT-F05-06

- [x] T004 [F05-RF-02][F05-RF-06][F05-RF-08][F05-RF-09][F05-RF-10][F05-RF-11][F05-RF-12] Grafo LangGraph + prompt v1 (perguntar antes de inventar, dividir, `human-only`, avaliar issue existente) — teste: integração com LLM roteirizado — 1,5 d
- [x] T005 [F05-RF-02] Serviço de chat: histórico, janela/sumarização, persistência, uso — teste: `test_chat_service.py` e `integration/test_chat.py` (emulador) — 1,5 d
- [x] T006 [F05-RF-01][F05-RF-07] Endpoint SSE + esquema de eventos (`docs/api/sse-events.v1.json`) + contrato — teste: `test_chat_api.py` — 1 d

---

### Fase 5: Validação e entrega

**Objetivo:** Aceitação em dev e evals não piores que o baseline.

**Aceitação:** AT-F05-01..09

- [x] T007 Testes de aceitação AT-F05-01..09 + evals comparadas ao baseline — teste: acceptance + evals — 1,5 d
