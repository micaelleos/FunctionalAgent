# Bootstrap da infraestrutura do SpecFlow AI (F02, tarefa T001)

Passos manuais **únicos**. Tudo depois disto é feito pelo Terraform (`infra/terraform`, workflow
`infra.yml`) e pelo pipeline (`deploy.yml`, `preview.yml`).

## Contexto (decisões do PO, 2026-11-14)

- O app vive no projeto **compartilhado do portfólio `pcb-inspect`**, junto com outros apps.
- **Um ambiente só** (produção) + previews por PR. Sem `dev`, sem `stg`, sem domínio próprio.
- URL: `https://specsflow-ai.web.app` (site já criado no console).
- Região `us-central1`; Cloud Run com `min-instances=0`.
- Isolamento: todo recurso do app tem o prefixo `specflow`. O Terraform **não** altera o banco
  Firestore `(default)`, a configuração de Auth do projeto, o orçamento nem recursos de outros apps
  (F02-RT-09).

| Recurso | Nome |
|---|---|
| Firestore (banco próprio) | `specflow` |
| Cloud Run | `specflow-api` |
| Artifact Registry | `specflow` |
| KMS keyring / chave | `specflow` / `jira-tokens` |
| Secret Manager | `specflow-llm-api-key` |
| Service accounts | `specflow-api`, `specflow-deployer`, `specflow-terraform` |
| WIF pool | `specflow-github` |
| Firebase web app | `SpecFlow AI` |
| Hosting | site `specsflow-ai` (importado) |
| Estado do Terraform | `gs://pcb-inspect-tfstate`, prefixo `specflow/prd` |

Pré-requisitos: `gcloud` autenticado (`gcloud auth login` e `gcloud auth application-default login`)
com papel de Owner no `pcb-inspect`; Terraform 1.9.x; admin do repositório no GitHub.

## 1. Bucket do estado do Terraform (F02-RT-08)

Um bucket para o portfólio; cada app usa o próprio prefixo. Pule se ele já existir.

```bash
PROJECT=pcb-inspect
gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com --project "$PROJECT"
gcloud storage buckets create "gs://$PROJECT-tfstate" --project "$PROJECT" --location us-central1 \
  --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update "gs://$PROJECT-tfstate" --versioning
```

## 2. Primeiro apply (local)

Cria, entre outros recursos, o Workload Identity Federation e a SA `specflow-terraform` que o
`infra.yml` usa dali em diante. Também **importa** o site `specsflow-ai` já existente.

```bash
cd infra/terraform
terraform init -backend-config=envs/prd.backend.hcl -reconfigure
terraform plan -var-file=envs/prd.tfvars     # confira: só recursos specflow-* e o site specsflow-ai
terraform apply -var-file=envs/prd.tfvars
terraform output -json github_variables
```

## 3. GitHub

1. **Settings → Secrets and variables → Actions → Variables** (do repositório): cadastre os
   valores de `terraform output -json github_variables` (`GCP_PROJECT_ID`, `GCP_REGION`,
   `GCP_WIF_PROVIDER`, `GCP_DEPLOYER_SA`, `GCP_TERRAFORM_SA`, `GCP_ARTIFACT_REPO`,
   `CLOUD_RUN_SERVICE`, `FIREBASE_SITE_ID`). Depois, `INFRA_ENABLED=true` e
   `DEPLOY_ENABLED=true`. Enquanto essas duas não existirem, só as verificações estáticas rodam.
2. **Settings → Environments**:

   | Environment | Revisores obrigatórios | Usado por |
   |---|---|---|
   | `prd` | **sim** (dono do produto) — AT-F02-02 | `deploy.yml` |
   | `preview` | — | `preview.yml` |
   | `infra-prd` | **sim** | `infra.yml` |

   O WIF só emite credenciais para jobs deste repositório nesses environments: `prd`/`preview`
   para a SA `specflow-deployer` e `infra-prd` para a SA `specflow-terraform`.
3. **Issues → Labels**: crie a label `preview` (F02-RF-04).
4. **Settings → Branches**: proteja `master` (PR obrigatório, 1 review, checks de `ci` verdes,
   histórico linear). Isto também fecha a tarefa T005 da F01.

## 4. Firebase Auth (antes da F03)

O Auth é do projeto e compartilhado com os outros apps. Por isso não fica no Terraform. No console
(Authentication → Settings → Authorized domains), confirme que `specsflow-ai.web.app` está na
lista. Os provedores de login (e-mail/senha, Google) são configurados na F03.

## 5. Verificação (Gate 3 da F02)

| Requisito | Comando | Esperado |
|---|---|---|
| F02-RT-01 | `terraform plan -detailed-exitcode -var-file=envs/prd.tfvars` | exit 0 (sem diferenças) |
| F02-RT-02 | `for sa in specflow-api specflow-deployer specflow-terraform; do gcloud iam service-accounts keys list --iam-account $sa@pcb-inspect.iam.gserviceaccount.com --managed-by user; done` | listas vazias |
| F02-RT-03 | `gcloud projects get-iam-policy pcb-inspect --flatten bindings --filter "bindings.members:specflow-api@" --format "table(bindings.role, bindings.condition.title)"` | `datastore.user` (condição `specflow-database-only`), `firebaseauth.viewer`, `cloudtrace.agent`, `logging.logWriter` |
| F02-RT-04 | `gcloud firestore databases describe --database specflow --project pcb-inspect --format "value(pointInTimeRecoveryEnablement)"` | `POINT_IN_TIME_RECOVERY_ENABLED` |
| F02-RT-05 | `gcloud run services describe specflow-api --region us-central1 --project pcb-inspect --format yaml` | `timeoutSeconds: 300`, `containerConcurrency: 40`, imagem `@sha256:`, `startupProbe` em `/healthz` |
| F02-RT-06 | `curl -sI https://specsflow-ai.web.app` | CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy` |
| F02-RT-08 | `gcloud storage buckets describe gs://pcb-inspect-tfstate --format "value(versioning_enabled)"` | `True` |
| F02-RT-09 | revisar o `plan` do passo 2 | nenhum recurso fora de `specflow-*` / `specsflow-ai` |

## 6. Segredo do LLM (antes da F05)

O Terraform cria só o contêiner do segredo; o valor nunca passa pelo estado:

```bash
printf '%s' "$CHAVE" | gcloud secrets versions add specflow-llm-api-key --data-file=- --project pcb-inspect
```
