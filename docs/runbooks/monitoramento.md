# Runbook — monitoramento

O monitoramento vem de `infra/terraform/modules/monitoring`: métricas por log, o dashboard
"specflow: operação" (Cloud Monitoring), o uptime check `specflow-api-health` (`/health`) e o SLO de
disponibilidade (99,5% em 28 dias).

**Sem alertas por e-mail desde 2026-11-20** (decisão do PO, por custo: ≈ US$ 9/mês pelas 6
condições). O custo do Gemini fica limitado pelo teto mensal do beta (F12-RF-05,
[custo.md](custo.md)), e o PO olha o dashboard 1×/dia durante o beta.

## O que olhar no dashboard

| Painel | Sinal de problema | Primeiro passo |
|---|---|---|
| Requisições por status | 5xx acima de ~2% | Logs com `severity>=ERROR` da revisão atual; se começou num deploy, [rollback](rollback.md) |
| Duração do turno / 1º token (p95) | turno > 30 s | Se o 1º token também subiu, é o modelo (Vertex AI); veja o `turn-timeout` |
| Turnos com erro | `llm-unavailable` frequente | Cota ou indisponibilidade do Vertex AI |
| Escritas no Jira | falhas seguidas | [jira-fora-do-ar.md](jira-fora-do-ar.md) |
| Tokens e custo estimado | subida rápida | [custo.md](custo.md) |
| Cota e rate limit atingidos | `beta-budget-exhausted` | O teto do mês acabou: [limites-e-app-check.md](limites-e-app-check.md) |
| Uptime check | falha em mais de uma região | `curl -s https://<api>/health`; revisões e tráfego em [rollback](rollback.md) |

## Recriar os alertas (se o PO decidir)

As políticas removidas estão no histórico do Git (`git log -- infra/terraform/modules/monitoring`,
antes de 2026-11-20). Para voltar: restaure o canal de e-mail e as políticas no módulo, a variável
`alert_email` (sensível; o repositório é público, então ela entra só por `TF_VAR_alert_email` no apply,
nunca no tfvars) e o `scripts/test_monitoring.py`. Atualize a F11-RF-04 na spec no mesmo PR.
