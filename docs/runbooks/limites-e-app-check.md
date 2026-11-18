# Runbook — cota, rate limit e App Check

## Cota diária e rate limit (F11-RT-05/06)

- Por usuário e por dia de Brasília: `DAILY_MESSAGE_QUOTA` (20) e `DAILY_TOKEN_QUOTA` (200 mil),
  contados em `users/{uid}/usage/{AAAA-MM-DD}`. Renova às 00:00 de Brasília.
- Rate limit: 10 mensagens em 60 s (`RATE_LIMIT_PER_MINUTE`), no mesmo documento.
- Liberar um usuário hoje (pedido legítimo): apague o documento do dia dele no console do Firestore
  (`users/<uid>/usage/<dia>`); o `uid` vem do pedido do usuário, não dos logs (lá só há `uid_hash`).
- Métrica: dashboard "Cota e rate limit atingidos".

## App Check (F11-RT-07)

O SPA manda o token do reCAPTCHA Enterprise; a API decide pelo `APP_CHECK_MODE`:

| Modo | Efeito |
|---|---|
| `off` | não verifica (local/testes) |
| `monitor` | verifica e só registra `event=app_check` (`missing`/`invalid`) |
| `enforce` | recusa com 401 `app-check-required` |

Ir para `enforce` (T008): depois de 1 semana em `monitor`, confira no dashboard "App Check sem token
válido" que só aparecem chamadas de fora do SPA (curl, scripts). Então mude `app_check_mode` no
`envs/prd.tfvars`, aplique o Terraform e rode o AT-F11-04. Voltar: `app_check_mode = "monitor"`, ou
na hora:

```bash
gcloud run services update "$SERVICE" --project "$PROJECT" --region "$REGION" \
  --update-env-vars APP_CHECK_MODE=monitor
```

O App Check não é exigido nos serviços do Firebase do projeto (Auth/Firestore são compartilhados com
outros apps); só a API do SpecFlow verifica.
