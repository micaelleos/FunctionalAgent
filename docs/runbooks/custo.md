# Runbook — custo do LLM disparou

O dashboard mostra o custo **estimado** que a API registra em cada `chat_turn` (`cost_usd`, preços em
`LLM_PRICE_*`). O billing real e o budget são do projeto compartilhado e não são geridos pelo app.
Não há alerta por e-mail (removido em 2026-11-20): o teto é o limite mensal do beta.

**Teto mensal do beta (F12-RF-05):** `MONTHLY_TOKEN_BUDGET` (Terraform `monthly_token_budget`,
padrão 5 milhões ≈ US$ 3,50) soma os tokens de todos os usuários no mês de Brasília
(`app_usage/{AAAA-MM}` no Firestore `specflow`). Ao atingir, o chat responde 429
`beta-budget-exhausted` para todos até o dia 1º. Para mudar na hora, sem deploy (vale no próximo
turno; `0` desliga):

```bash
gcloud run services update "$SERVICE" --project "$PROJECT" --region "$REGION" \
  --update-env-vars MONTHLY_TOKEN_BUDGET=10000000
```

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
5. Alinhe o Terraform (`daily_message_quota`, `daily_token_quota`, `monthly_token_budget`) se a
   mudança ficar; o próximo `terraform apply` volta ao valor do Terraform.
