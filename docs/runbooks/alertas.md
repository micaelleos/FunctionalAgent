# Runbook — alertas

Os alertas vêm de `infra/terraform/modules/monitoring` e chegam por e-mail ao responsável. O
dashboard "specflow: operação" (Cloud Monitoring) mostra requisições, turnos, latência, tokens,
ações, escritas no Jira, limites, App Check e erros do front.

| Alerta | Primeiro passo |
|---|---|
| `specflow: API 5xx > 2%` | Logs com `severity>=ERROR` da revisão atual; se começou num deploy, [rollback](rollback.md) |
| `specflow: p95 do turno > 30 s` | Dashboard: o 1º token também subiu? Então é o modelo (Vertex); veja o status do Vertex AI e o `turn-timeout` |
| `specflow: erro do modelo > 5%` | `jsonPayload.event="chat_turn" AND jsonPayload.error!=""`: `llm-unavailable` é cota/indisponibilidade do Vertex |
| `specflow: falhas ao escrever no Jira` | [jira-fora-do-ar.md](jira-fora-do-ar.md) |
| `specflow: API fora do ar (uptime /health)` | `curl -s https://<api>/health`; revisões e tráfego em [rollback](rollback.md) |
| `specflow: custo estimado de LLM > US$ N/dia` | [custo.md](custo.md) |

## Aplicar ou mudar o monitoramento

O e-mail não fica no repositório (é público). Aplique com ele no ambiente:

```bash
cd infra/terraform
terraform init -backend-config=envs/prd.backend.hcl
TF_VAR_alert_email='<e-mail do responsável>' terraform plan -var-file=envs/prd.tfvars -out=f11.plan
terraform apply f11.plan   # só com aprovação do PO
```

## Ensaio do alerta (AT-F11-03)

Aponta o uptime check para uma rota que responde 404, espera o incidente e volta. A API não muda.

```bash
TF_VAR_alert_email='…' terraform apply -var-file=envs/prd.tfvars -var uptime_path=/ensaio-alerta
# ~15 min: incidente aberto no Monitoring e e-mail "API fora do ar (uptime /health)"
TF_VAR_alert_email='…' terraform apply -var-file=envs/prd.tfvars   # volta para /health
```

Registre na seção de evidências da F11 o horário do e-mail e do fechamento do incidente.
