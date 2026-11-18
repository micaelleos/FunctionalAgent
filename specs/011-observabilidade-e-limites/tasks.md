# F11 — Observabilidade, limites de uso e proteção — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · formato do `tasks-template` do projeto.

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

**Total:** 8 tarefas · 6 d. Revisão 2026-11-18: T003 dividida (T003/T006), T007 (erros do front), T008 (App Check em
`enforce` após 1 semana, fora deste PR).

## 8. Tarefas

### Fase 1: Fundação

**Aceitação:** AT-F11-04

- [ ] T001 Logs JSON com contexto, `uid_hash` e traces OTel — teste: `test_logging.py` — 1 d
- [ ] T002 [P] App Check (front + back, modo `monitor`) — teste: `test_app_check.py`, `api.test.ts` — 0,5 d
- [ ] T007 [P] Erros do front → Error Reporting — teste: `test_client_errors.py`, `errorReporting.test.ts` — 0,5 d

### Fase 2: Incremento 1 — limites de uso

**Aceitação:** AT-F11-01, AT-F11-02

- [ ] T003 [F11-RF-02][F11-RF-03] Cota diária + rate limit no Firestore — teste: `test_usage.py`, integração — 1 d
- [ ] T006 [F11-RF-01] `GET /me/usage` + indicador e painel — teste: `UsagePanel.test.tsx`, `ChatPage.test.tsx` — 0,5 d

### Fase 3: Incremento 2 — alertas

**Aceitação:** AT-F11-03

- [ ] T004 [F11-RF-04] Métricas por log, dashboard, alertas, uptime, SLO (Terraform) — teste: AT-F11-03 — 1 d

### Fase 4: Validação e entrega

- [ ] T005 Carga k6, ZAP, runbooks — teste: k6/ZAP — 1 d
- [ ] T008 App Check `enforce` após 1 semana em `monitor` (PR à parte) — teste: AT-F11-04 em prd — 0,25 d
