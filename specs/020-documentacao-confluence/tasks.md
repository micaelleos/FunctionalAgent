# F20 — Documentação do projeto no Confluence — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição em caminho/do/arquivo — teste: <teste> — <est.>`

**Total:** 14 tarefas · ≈ 6 d

## 8. Tarefas

### Fase 1: Preparação (contrato primeiro)

- [x] T001 `kind` e payloads `create_space`, `create_page`, `update_page` nas ações propostas (backend/app/services/actions.py) e `diff` no SSE `action_proposed` (docs/api/sse-events.v1.json) — teste: backend/tests/unit/test_confluence_actions.py — 0,5 d

---

### Fase 2: Fundação

- [x] T002 Escrita no `ConfluenceClient` (spaces, pages create/update com versão, labels; sem retry; 409) em backend/app/integrations/confluence/client.py — teste: backend/tests/unit/test_confluence_client_write.py (respx) — 0,5 d
- [x] T003 [P] Markdown → storage determinístico em backend/app/integrations/confluence/storage.py — teste: backend/tests/unit/test_confluence_storage.py (ida e volta) — 0,5 d
- [x] T004 [P] Diff por seção em backend/app/services/page_diff.py — teste: backend/tests/unit/test_page_diff.py — 0,5 d
- [x] T005 [P] Modelos em backend/app/agent/templates/confluence/ a partir de docs/metodologia/modelos/ — teste: backend/tests/unit/test_templates_in_sync.py — 0,25 d
- [x] T006 [P] Repositório `users/{uid}/documents` e flag `CONFLUENCE_WRITE_ENABLED` em backend/app/repositories/documents.py e core/config.py — teste: backend/tests/integration/test_documents_repo.py — 0,25 d

---

### Fase 3: Incremento 1 — páginas por ação proposta ([F20-RF-02], [F20-RF-03], [F20-RF-04], [F20-RF-07])

**Aceitação:** AT-F20-02, AT-F20-04, AT-F20-05

- [x] T007 [F20-RF-02] [F20-RF-03] Ferramentas `propor_criacao_pagina` e `propor_atualizacao_pagina` em backend/app/agent/tools/confluence_tools.py — teste: backend/tests/unit/test_confluence_page_tools.py — 0,5 d
- [x] T008 [F20-RF-04] [F20-RF-07] Execução na confirmação (hash, versão, 409, Registro de mudanças, auditoria) em backend/app/services/confluence_actions.py — teste: backend/tests/unit/test_confluence_actions.py — 1 d
- [x] T009 [P] [F20-RF-03] Cartão da proposta com diff e erro de conflito em frontend/src/components/ActionCard.tsx — teste: ActionCard.test.tsx — 0,5 d

---

### Fase 4: Incremento 2 — espaço e convergência ([F20-RF-01], [F20-RF-05], [F20-RF-06])

**Aceitação:** AT-F20-01, AT-F20-03

- [x] T010 [F20-RF-01] `propor_criacao_espaco` + execução com o modelo (`confluence-partial`) e botão "Create space" em Projects (abre o chat do projeto) — teste: backend/tests/unit/test_confluence_actions.py, ProjectsPage.test.tsx — 1 d
- [x] T011 [F20-RF-05] [F20-RF-06] Fase Convergir com escrita e ADR no `system_v2.md` — teste: evals `confluence-converge-write-*`, `confluence-adr-*`, `confluence-no-spam-*` — 0,5 d

---

### Fase 5: Incremento 3 — aba "Docs" ([F20-RF-08])

- [x] T012 [F20-RF-08] `GET /api/v1/documents` e aba "Docs" em frontend/src/pages/IssuesPage.tsx — teste: IssuesPage.test.tsx, backend/tests/unit/test_documents_api.py — 0,5 d

---

### Fase 6: Validação e entrega

- [x] T013 [P] `confluence_write` nos logs, métrica e painel — teste: backend/tests/unit/test_telemetry.py, scripts/test_monitoring.py — 0,25 d
- [ ] T014 AT-F20-01..05 no Confluence do sandbox (com aprovação do PO), rastreabilidade e evidências (Playwright pronto em frontend/e2e/f20-confluence-escrita.spec.ts; falta rodar) — teste: Playwright, `make trace` — 0,5 d
