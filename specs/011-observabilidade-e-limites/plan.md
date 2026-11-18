# F11 — Observabilidade, limites de uso e proteção — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico
### 7. Desenho
- **Logs (`core/logging.py`):** formatter JSON (stdlib, sem dependência nova) instalado no startup; middleware
  `RequestContextMiddleware` guarda `request_id` (header `X-Request-Id` ou gerado) e o trace do
  `X-Cloud-Trace-Context`/`traceparent` em `contextvars`; `uid_hash` entra quando o token é verificado. Os eventos
  existentes (`chat_turn`, `jira_write`) passam a `log.info("chat_turn", extra={"fields": {...}})` e ganham
  `first_token_ms`.
- **Traces (`core/telemetry.py`):** OpenTelemetry SDK + exporter do Cloud Trace + propagador GCP, instrumentação httpx
  (Jira) e spans manuais (`chat.turn`, `llm.call`); só com `TRACING_ENABLED=true`.
- **Cota e rate limit (`services/usage.py`, `repositories/usage.py`):** `reserve(uid)` numa transação em
  `users/{uid}/usage/{AAAA-MM-DD de Brasília}`: confere a janela de 60 s (`recent`, até 10 instantes) e a cota
  (`messages`, `inputTokens + outputTokens`), incrementa `messages` e grava o instante. Chamado em `open_turn` antes de
  gravar a mensagem; erros 429 `quota-exceeded` (`resets_at`) e `rate-limited` (`Retry-After`). `add_usage` deixa de
  contar mensagens. `GET /api/v1/me/usage` → hoje, limites, `resets_at`, últimos 7 dias.
- **App Check (`core/app_check.py`, dependência em `CurrentUser`):** `firebase_admin.app_check.verify_token`;
  `APP_CHECK_MODE` off/monitor/enforce. Front: `@firebase/app-check` com `ReCaptchaEnterpriseProvider` quando
  `VITE_APPCHECK_SITE_KEY` existe; `apiFetch` e o SSE mandam o header.
- **Erros do front:** `POST /api/v1/client-errors` (corpo ≤ 8 KB, campos truncados) → log `ERROR` com `@type` do
  Error Reporting; `frontend/src/lib/errorReporting.ts` + `ErrorBoundary`.
- **Terraform:** módulo `monitoring` (métricas por log, dashboard, uptime check, canal de e-mail, políticas, serviço e
  SLO); `recaptcha` + App Check do web app no módulo `firebase`; APIs `recaptchaenterprise` e `firebaseappcheck`;
  variáveis de cota/App Check/tracing no Cloud Run. Apply local com aprovação do PO, e-mail por `TF_VAR_alert_email`.
- **Carga e segurança:** `scripts/load/chat.js` (k6 em Docker), `.github/workflows/zap.yml` (baseline, manual e no PR
  que o altera).

### 9. Plano de testes
Unit (logs, cota, rate limit, App Check, client-errors), integração no emulador (transação da cota), Vitest (uso,
mensagens de 429, reporte de erros), AT-F11-01/02 E2E local com cota 3, AT-F11-03 ensaio do uptime em prd,
AT-F11-04 integração com `enforce`; k6 e ZAP.

### Rollback
`APP_CHECK_MODE=off`, `DAILY_MESSAGE_QUOTA` alto ou reverter o merge; `terraform destroy -target=module.monitoring`
remove só os recursos `specflow` de monitoramento.
