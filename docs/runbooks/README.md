# Runbooks — SpecFlow AI

Variáveis usadas em todos: `PROJECT=pcb-inspect`, `REGION=us-central1`, `SERVICE=specflow-api`,
`SITE=specsflow-ai`, `DB=specflow`. Projeto compartilhado do portfólio: só mexa em recursos
`specflow*` (F02-RT-09).

| Situação | Runbook |
|---|---|
| Deploy ruim, voltar versão | [rollback.md](rollback.md) |
| Chegou um alerta / ensaio de alerta | [alertas.md](alertas.md) |
| Dados apagados ou corrompidos no Firestore | [firestore-restauracao.md](firestore-restauracao.md) |
| Token do Jira ou credencial do GCP vazou | [credencial-vazada.md](credencial-vazada.md) |
| Jira fora do ar ou recusando | [jira-fora-do-ar.md](jira-fora-do-ar.md) |
| Custo do LLM disparou | [custo.md](custo.md) |
| Cota, rate limit e App Check | [limites-e-app-check.md](limites-e-app-check.md) |

Logs da API (JSON, um evento por linha): `gcloud logging read 'resource.type="cloud_run_revision"
AND resource.labels.service_name="specflow-api" AND jsonPayload.event="chat_turn"' --project
"$PROJECT" --freshness=1h`. Os logs têm `uid_hash`, nunca o `uid` nem o conteúdo das mensagens.
