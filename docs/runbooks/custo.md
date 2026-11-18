# Runbook — custo do LLM disparou

O alerta usa o custo **estimado** que a API registra em cada `chat_turn` (`cost_usd`, preços em
`LLM_PRICE_*`). O billing real e o budget são do projeto compartilhado e não são geridos pelo app.

1. Quem está gastando: `jsonPayload.event="chat_turn"` agrupado por `uid_hash` (Logs Explorer →
   "Summarize"); tokens altos por turno indicam conversa longa ou laço de ferramentas.
2. Se é um usuário: a cota diária já limita (`DAILY_MESSAGE_QUOTA`, `DAILY_TOKEN_QUOTA`). Para conter
   na hora, baixe a cota de todos (vale no próximo turno):

```bash
gcloud run services update "$SERVICE" --project "$PROJECT" --region "$REGION" \
  --update-env-vars DAILY_MESSAGE_QUOTA=5,DAILY_TOKEN_QUOTA=50000
```

3. Se é abuso de fora do app: veja o dashboard "App Check sem token válido" e considere
   `APP_CHECK_MODE=enforce` ([limites-e-app-check.md](limites-e-app-check.md)).
4. Parar o chat inteiro: `VITE_FEATURE_CHAT=false` no build do SPA (rollback da F08) ou escalar o
   Cloud Run para 0 instâncias máximas — só em último caso.
5. Alinhe o Terraform (`daily_message_quota`, `daily_token_quota`) se a mudança ficar.
