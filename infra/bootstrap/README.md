# Bootstrap da infraestrutura (F02, tarefa T001)

Passos manuais **únicos** por ambiente. Tudo depois disto é feito pelo Terraform
(`infra/terraform`, workflow `infra.yml`) e pelo pipeline (`deploy.yml`, `preview.yml`).

Decisões do dono do produto (2026-11-14): região `us-central1`, ambientes `dev` e `prd`
(sem `stg`), sem domínio próprio (URLs `*.web.app` e `*.run.app`), `min-instances=0` também em prd.

Pré-requisitos: `gcloud` autenticado com uma conta que possa criar projetos e associar a conta de
faturamento; Terraform 1.9.x; acesso de administrador ao repositório no GitHub.

## 1. Projetos e faturamento

```bash
BILLING=XXXXXX-XXXXXX-XXXXXX          # gcloud billing accounts list
for ENV in dev prd; do
  gcloud projects create "functional-agent-$ENV" --name "Agente Funcional ($ENV)"
  gcloud billing projects link "functional-agent-$ENV" --billing-account "$BILLING"
  # APIs mínimas para o Terraform conseguir habilitar as demais
  gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com \
    --project "functional-agent-$ENV"
done
```

## 2. Bucket do estado do Terraform (F02-RT-08)

```bash
for ENV in dev prd; do
  gcloud storage buckets create "gs://functional-agent-tfstate-$ENV" \
    --project "functional-agent-$ENV" --location us-central1 \
    --uniform-bucket-level-access --public-access-prevention
  gcloud storage buckets update "gs://functional-agent-tfstate-$ENV" --versioning
done
```

## 3. Primeiro apply (local)

O primeiro apply cria, entre outros recursos, o Workload Identity Federation e a service account
`terraform@` que o `infra.yml` usa dali em diante. Ele precisa ser feito por uma pessoa:

```bash
gcloud auth application-default login
cd infra/terraform
export TF_VAR_billing_account_id="$BILLING"
ENV=dev   # depois repita com ENV=prd
terraform init -backend-config="envs/$ENV.backend.hcl" -reconfigure
terraform apply -var-file="envs/$ENV.tfvars"
terraform output -json github_environment_variables
```

O budget alert (F02-RT-07) é criado na conta de faturamento. A conta que roda o Terraform precisa
do papel **Billing Account Costs Manager** nessa conta; conceda o mesmo papel à SA
`terraform@functional-agent-$ENV.iam.gserviceaccount.com` para os applies seguintes pelo
`infra.yml`:

```bash
gcloud billing accounts add-iam-policy-binding "$BILLING" \
  --member "serviceAccount:terraform@functional-agent-$ENV.iam.gserviceaccount.com" \
  --role roles/billing.costsManager
```

## 4. GitHub

Em **Settings → Environments**, crie os ambientes abaixo. Os valores vêm de
`terraform output -json github_environment_variables` do ambiente correspondente.

| Environment | Revisores obrigatórios | Variables |
|---|---|---|
| `dev` | — | `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_DEPLOYER_SA`, `GCP_ARTIFACT_REPO`, `CLOUD_RUN_SERVICE`, `FIREBASE_SITE_ID` |
| `prd` | **sim** (dono do produto) — AT-F02-02 | as mesmas, com os valores de prd |
| `infra-dev` | — | `GCP_WIF_PROVIDER`, `GCP_TERRAFORM_SA`, `GCP_BILLING_ACCOUNT` (de dev) |
| `infra-prd` | **sim** | `GCP_WIF_PROVIDER`, `GCP_TERRAFORM_SA`, `GCP_BILLING_ACCOUNT` (de prd) |

O provider WIF só emite credenciais para jobs deste repositório que rodam nesses environments:
`<env>` para a SA `deployer@` e `infra-<env>` para a SA `terraform@`.

Depois:

1. **Settings → Secrets and variables → Actions → Variables** (repositório):
   `INFRA_ENABLED=true` e `DEPLOY_ENABLED=true`. Enquanto não existirem, `infra.yml` só roda
   as verificações estáticas e `deploy.yml`/`preview.yml` não rodam.
2. **Issues → Labels**: crie a label `preview` (F02-RF-04).
3. **Settings → Branches**: proteja `master` (PR obrigatório, 1 review, checks de `ci` verdes,
   histórico linear). Isto também fecha a tarefa T005 da F01.

## 5. Verificação (Gate 3 da F02)

| Requisito | Comando | Esperado |
|---|---|---|
| F02-RT-01 | `terraform plan -detailed-exitcode -var-file=envs/$ENV.tfvars` | exit 0 (sem diferenças) |
| F02-RT-02 | `for sa in api-runtime deployer terraform; do gcloud iam service-accounts keys list --iam-account $sa@functional-agent-$ENV.iam.gserviceaccount.com --managed-by user; done` | listas vazias |
| F02-RT-03 | `gcloud projects get-iam-policy functional-agent-$ENV --flatten bindings --filter "bindings.members:api-runtime@" --format "value(bindings.role)"` | só `datastore.user`, `firebaseauth.viewer`, `cloudtrace.agent`, `logging.logWriter` |
| F02-RT-04 | `gcloud firestore databases describe --project functional-agent-prd --format "value(pointInTimeRecoveryEnablement)"` | `POINT_IN_TIME_RECOVERY_ENABLED` (prd) |
| F02-RT-05 | `gcloud run services describe api --region us-central1 --project functional-agent-$ENV --format yaml` | `timeoutSeconds: 300`, `containerConcurrency: 40`, imagem `@sha256:`, `startupProbe` em `/healthz` |
| F02-RT-06 | `curl -sI https://functional-agent-$ENV.web.app` | CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy` |
| F02-RT-07 | console de faturamento → Orçamentos | limites 50/90/100% |
| F02-RT-08 | `gcloud storage buckets describe gs://functional-agent-tfstate-$ENV --format "value(versioning_enabled)"` | `True` |

## 6. Segredo do LLM (antes da F05)

O Terraform cria só o contêiner `llm-api-key`; o valor nunca passa pelo estado:

```bash
printf '%s' "$CHAVE" | gcloud secrets versions add llm-api-key --data-file=- --project functional-agent-$ENV
```
