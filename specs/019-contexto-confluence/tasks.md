# F19 — Contexto do Confluence e metodologia em fases no agente — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição em caminho/do/arquivo — teste: <teste> — <est.>`

**Total:** 17 tarefas · ≈ 6 d

## 8. Tarefas

### Fase 1: Preparação (contrato primeiro)

- [ ] T001 Rotas e esquemas `/api/v1/projects/{key}/confluence` e `/api/v1/confluence/spaces` em backend/app/api/v1/confluence.py (respostas 501 até a Fase 3) — teste: backend/tests/contract/test_confluence_api.py — 0,5 d
- [ ] T002 [P] `AgentReadySpec` v2 (`references`, `conflicts` na proposta) em backend/app/agent/spec/schema.py e render.py; SSE `action_proposed.conflicts` em docs/api/sse-events.v1.json; `make api-types` — teste: backend/tests/unit/test_spec_schema.py, test_render.py — 0,5 d

---

### Fase 2: Fundação

- [ ] T003 `ConfluenceClient` (spaces, page, children, search CQL; auth, retries, sem redirect, erros) em backend/app/integrations/confluence/client.py — teste: backend/tests/unit/test_confluence_client.py (respx) — 1 d
- [ ] T004 [P] Storage format → Markdown com truncagem em backend/app/integrations/confluence/markdown.py — teste: backend/tests/unit/test_confluence_markdown.py — 0,5 d
- [ ] T005 [P] Repositório `users/{uid}/project_links` em backend/app/repositories/project_links.py — teste: backend/tests/integration/test_project_links_repo.py (emulador) — 0,25 d
- [ ] T006 [P] Config `CONFLUENCE_ENABLED` (o `PROMPT_VERSION` já existe) em backend/app/core/config.py e infra/terraform/modules/cloud_run/main.tf — teste: backend/tests/unit/test_config.py, `terraform validate` — 0,25 d

**Checkpoint:** cliente e vínculo prontos.

---

### Fase 3: Incremento 1 — vínculo projeto ↔ espaço ([F19-RF-01], [F19-RF-02])

**Aceitação:** AT-F19-01

- [ ] T007 [F19-RF-01] Descoberta (mesma chave → rótulo) e vincular/desvincular em backend/app/services/confluence_links.py; rotas da T001 — teste: backend/tests/unit/test_confluence_links.py — 0,5 d
- [ ] T008 [P] [F19-RF-02] Cartão "Confluence" com sugestão, "Link", troca e desvínculo em frontend/src/pages/ProjectsPage.tsx e product/http.ts — teste: ProjectsPage.test.tsx, frontend/e2e/f19-confluence.spec.ts (AT-F19-01) — 1 d

---

### Fase 4: Incremento 2 — leitura pelo agente e fases ([F19-RF-03], [F19-RF-04], [F19-RF-06], [F19-RF-09])

**Aceitação:** AT-F19-02, AT-F19-04, AT-F19-05

- [ ] T009 [F19-RF-03] `ConfluenceReader` + adaptador e ferramentas `listar_documentos_do_projeto`, `buscar_paginas_confluence`, `ler_pagina_confluence` (CQL montada no código, limites, `dados_confluence`) em backend/app/agent/tools/confluence_tools.py, context.py, services/confluence_reader.py — teste: backend/tests/unit/test_confluence_tools.py — 1 d
- [ ] T010 [F19-RF-04] [F19-RF-09] Fase Descobrir no `ChatService` (páginas fixas no 1º turno, progresso, sem acesso → aviso único) em backend/app/services/chat.py — teste: backend/tests/unit/test_chat_confluence.py — 0,5 d
- [ ] T011 [F19-RF-06] Prompt `system_v2.md` com as 7 fases e "Referências"; seleção por `PROMPT_VERSION` em backend/app/agent/prompts/ e graph.py — teste: backend/tests/unit/test_prompts.py — 0,5 d

---

### Fase 5: Incremento 3 — verificar e convergir ([F19-RF-05], [F19-RF-07], [F19-RF-08])

**Aceitação:** AT-F19-03

- [ ] T012 [F19-RF-07] Filtro de conflitos por IDs vistos no turno em backend/app/agent/tools/jira_tools.py (propostas) — teste: backend/tests/unit/test_conflicts.py — 0,5 d
- [ ] T013 [P] [F19-RF-07] Aviso "Conflicts with …" no cartão da proposta em frontend/src/pages/ChatPage.tsx — teste: ChatPage.test.tsx, frontend/e2e/f19-confluence.spec.ts (AT-F19-03) — 0,5 d
- [ ] T014 [P] [F19-RF-05] [F19-RF-08] Evals com espaço de exemplo (contexto, esclarecer, conflito, injeção, convergir) em evals/datasets/confluence-* e evals/datasets/confluence_space/ — teste: `evals/run.py --compare` v2 ≥ v1 — 1 d

---

### Fase 6: Validação e entrega

- [ ] T015 [P] `confluence_read` nos logs, métrica por log e painel em backend/app/agent/tools/confluence_tools.py e infra/terraform/modules/monitoring/main.tf — teste: backend/tests/unit/test_telemetry.py, scripts/test_monitoring.py — 0,5 d
- [ ] T016 Emenda PATCH do Art. XII.5 (cita o Confluence) em .specify/memory/constitution.md e docs/modernizacao/02-constituicao.md; ADR-009 "Aceito" — teste: revisão do PO — 0,25 d
- [ ] T017 AT-F19-01..05 (02 e 04 no sandbox com o Gemini real), rastreabilidade e evidências em spec.md — teste: `make trace`, Playwright — 0,5 d

## Dependências e paralelismo
- Fases 1 → 2 → 3/4 (paralelas) → 5 → 6. A T010 depende da T009, e a T012 depende da T002.
- Um PR por incremento.
