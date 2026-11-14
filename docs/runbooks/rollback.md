# Runbook — rollback

Meta: voltar ao estado anterior em **menos de 5 minutos** (Constituição VIII.3, F02-RF-02).
Variáveis usadas abaixo: `PROJECT=pcb-inspect`, `REGION=us-central1`, `SERVICE=specflow-api`,
`SITE=specsflow-ai`.

O deploy é feito com `make deploy` (ADR-006). Se o smoke em `/health` falhar, o `make deploy-api` não
move tráfego: a revisão nova fica sem tráfego e a anterior continua servindo. O comando termina com a
linha `API: … (rollback: revisão <anterior>)`, que é o alvo do rollback abaixo.

## Backend (Cloud Run)

```bash
# Revisões e tráfego atuais
gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" \
  --format 'table(status.traffic[].revisionName, status.traffic[].percent, status.traffic[].tag)'
gcloud run revisions list --service "$SERVICE" --project "$PROJECT" --region "$REGION" --limit 5

# Volta 100% para a revisão anterior (< 2 min)
gcloud run services update-traffic "$SERVICE" --project "$PROJECT" --region "$REGION" \
  --to-revisions <revisao-anterior>=100
```

## Frontend (Firebase Hosting)

```bash
npx firebase-tools@13.35.1 hosting:rollback --project "$PROJECT" --site "$SITE"
```

`index.html` é servido com `Cache-Control: no-cache`, então o rollback vale no próximo carregamento.

## Ensaios (AT-F02-02 e AT-F02-03)

Faça a cada mudança no `scripts/deploy.sh` e registre o resultado em
`specs/002-infraestrutura-base/spec.md` §11.

1. **Smoke falho não move tráfego (AT-F02-02).** Anote a revisão que serve 100% e rode o deploy
   exigindo uma versão que a imagem não tem:
   ```bash
   EXPECTED_VERSION=ensaio-invalido make deploy-api   # esperado: "Smoke falhou", exit 1
   gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" \
     --format 'value(status.traffic[0].revisionName, status.traffic[0].percent)'
   ```
   Esperado: 100% continua na revisão anotada.
2. **Rollback em menos de 5 min (AT-F02-03).** Depois de um `make deploy-api` bem-sucedido,
   cronometre a volta para a revisão anterior:
   ```bash
   START=$(date +%s)
   gcloud run services update-traffic "$SERVICE" --project "$PROJECT" --region "$REGION" \
     --to-revisions <revisao-anterior>=100
   curl -fsS "$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" \
     --format 'value(status.url)')/health"
   echo "rollback em $(( $(date +%s) - START )) s"   # esperado: < 300 s
   ```
   Volte para a revisão nova com `--to-latest` ao terminar.

## Outros cenários

Prompt degradado, dados corrompidos e feature flags: ver `docs/modernizacao/06-cicd-deploy.md` §6.
