# Runbook — rollback

Meta: voltar ao estado anterior em **menos de 5 minutos** (Constituição VIII.3, F02-RF-02).
Variáveis usadas abaixo: `ENV=dev|prd`, `PROJECT=functional-agent-$ENV`, `REGION=us-central1`.

## Backend (Cloud Run)

O pipeline faz rollback automático quando o canário reprova (`deploy.yml`, passo
"Rollback automático"). Para fazer à mão:

```bash
# Revisões e tráfego atuais
gcloud run services describe api --project "$PROJECT" --region "$REGION" \
  --format 'table(status.traffic[].revisionName, status.traffic[].percent, status.traffic[].tag)'
gcloud run revisions list --service api --project "$PROJECT" --region "$REGION" --limit 5

# Volta 100% para a revisão anterior (< 2 min)
gcloud run services update-traffic api --project "$PROJECT" --region "$REGION" \
  --to-revisions <revisao-anterior>=100
```

## Frontend (Firebase Hosting)

```bash
npx firebase-tools@13.35.1 hosting:rollback --project "$PROJECT"
```

`index.html` é servido com `Cache-Control: no-cache`, então o rollback vale no próximo carregamento.

## Ensaio do canário (AT-F02-03)

Ensaio controlado em **dev**, sem mudar código da aplicação. Faça a cada mudança no `deploy.yml`
ou no `scripts/canary.py` e registre o tempo em `specs/002-infraestrutura-base/spec.md` §11.

1. Anote a revisão que serve 100% (`<estavel>`).
2. Crie uma revisão candidata com a imagem atual e uma tag de ensaio, e mande 10% do tráfego:
   ```bash
   IMAGE=$(gcloud run services describe api --project "$PROJECT" --region "$REGION" \
     --format 'value(spec.template.spec.containers[0].image)')
   gcloud run deploy api --project "$PROJECT" --region "$REGION" --image "$IMAGE" \
     --no-traffic --tag ensaio --quiet
   gcloud run services update-traffic api --project "$PROJECT" --region "$REGION" --to-tags ensaio=10
   ```
3. Rode o canário apontando para uma URL que responde 404 (simula `/healthz` quebrado) e
   cronometre:
   ```bash
   START=$(date +%s)
   GCP_ACCESS_TOKEN=$(gcloud auth print-access-token) python3 scripts/canary.py \
     --project "$PROJECT" --service api --revision <revisao-ensaio> \
     --url "https://ensaio---api-<hash>-uc.a.run.app/nao-existe" --interval 60
   gcloud run services update-traffic api --project "$PROJECT" --region "$REGION" \
     --to-revisions <estavel>=100
   echo "rollback em $(( $(date +%s) - START )) s"
   ```
   Esperado: o canário sai com código 1 após duas falhas seguidas (~1–2 min) e o total fica
   abaixo de 300 s.
4. Limpe a tag: `gcloud run services update-traffic api --project "$PROJECT" --region "$REGION" --remove-tags ensaio`.

## Outros cenários

Prompt degradado, dados corrompidos e feature flags: ver `docs/modernizacao/06-cicd-deploy.md` §6.
