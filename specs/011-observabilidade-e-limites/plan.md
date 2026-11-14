# F11 — Observabilidade, limites de uso e proteção — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico
### 7. Desenho
- `core/logging.py` (structlog → formato Cloud Logging), `core/telemetry.py` (OTel + exporter GCP), middleware de
  `request_id`/trace, `services/quota.py`, dependência `app_check()`.
- Terraform `monitoring`: log-based metrics, dashboard JSON, políticas de alerta, canal de e-mail, SLOs no Service Monitoring.
- `GET /api/v1/me/usage` para o indicador da UI.
### 9. Plano de testes
Integração para cotas e rate limit; ensaio de alerta em dev; carga com k6.
