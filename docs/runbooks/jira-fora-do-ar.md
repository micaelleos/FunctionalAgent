# Runbook — Jira fora do ar ou recusando

1. Status da Atlassian: https://jira-software.status.atlassian.com/.
2. Logs: `jsonPayload.event="jira_write" AND jsonPayload.result="failed"` mostra o `code`
   (`jira-forbidden`, `jira-rate-limited`, `jira-uncertain`, …) por ação.
3. Se o Jira está fora: nada a fazer no app. As propostas continuam pendentes por 24 h e o usuário
   confirma depois; a confirmação não executa duas vezes (F06-RT-01).
4. Se é `jira-credential-rejected` de um usuário: a conexão já foi marcada inválida e a UI pede um
   token novo; não é incidente.
5. Para parar as escritas sem deploy (ex.: comportamento estranho do Jira): `ACTIONS_ENABLED=false`
   no Cloud Run (as propostas ficam guardadas, nenhuma executa):

```bash
gcloud run services update "$SERVICE" --project "$PROJECT" --region "$REGION" \
  --update-env-vars ACTIONS_ENABLED=false
```

Volte com `ACTIONS_ENABLED=true` (e alinhe o Terraform se a mudança ficar).
