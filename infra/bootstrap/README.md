# Bootstrap da infraestrutura do SpecFlow AI (F02, tarefa T001)

Passos manuais **únicos**. Depois disto, a infraestrutura muda com `terraform apply` local
(`infra/terraform`) e as aplicações com `make deploy` (ADR-006, sem CI/CD).

## Contexto (decisões do PO, 2026-11-14)

- O app vive no projeto **compartilhado do portfólio `pcb-inspect`**, junto com outros apps.
- **Um ambiente só** (produção). Sem `dev`, sem `stg`, sem previews, sem domínio próprio.
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
| Service account (runtime) | `specflow-api` |
| Firebase web app | `SpecFlow AI` |
| Hosting | site `specsflow-ai` (importado) |
| Estado do Terraform | `gs://pcb-inspect-tfstate`, prefixo `specflow/prd` |

Pré-requisitos: `gcloud` autenticado (`gcloud auth login` e `gcloud auth application-default login`)
com papel de Owner no `pcb-inspect`; Terraform 1.9.x; Docker e Node 22 (para o `make deploy`).

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

Cria os recursos do app e **importa** o site `specsflow-ai` e o web app `SpecFlow AI` já existentes.
Sem ADC, exporte antes `GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)`.

```bash
cd infra/terraform
terraform init -backend-config=envs/prd.backend.hcl -reconfigure
terraform plan -var-file=envs/prd.tfvars     # confira: só recursos specflow-* e o site specsflow-ai
terraform apply -var-file=envs/prd.tfvars
```

## 3. Primeiro deploy

```bash
gcloud auth application-default login   # o firebase-tools usa ADC
make deploy                             # API (smoke em /health antes do tráfego) e depois o SPA
E2E_BASE_URL=https://specsflow-ai.web.app make e2e
```

## 4. Firebase Auth (antes da F03)

O Auth é do projeto e compartilhado com os outros apps. Por isso não fica no Terraform. No console
(Authentication → Settings → Authorized domains), confirme que `specsflow-ai.web.app` está na
lista. Os provedores de login (e-mail/senha, Google) são configurados na F03.

## 5. Verificação (Gate 3 da F02)

| Requisito | Comando | Esperado |
|---|---|---|
| F02-RT-01 | `terraform plan -detailed-exitcode -var-file=envs/prd.tfvars` | exit 0 (sem diferenças) |
| F02-RT-02 | `gcloud iam service-accounts keys list --iam-account specflow-api@pcb-inspect.iam.gserviceaccount.com --managed-by user` | lista vazia |
| F02-RT-03 | `gcloud projects get-iam-policy pcb-inspect --flatten bindings --filter "bindings.members:specflow-api@" --format "table(bindings.role, bindings.condition.title)"` | `datastore.user` (condição `specflow-database-only`), `firebaseauth.viewer`, `cloudtrace.agent`, `logging.logWriter` |
| F02-RT-04 | `gcloud firestore databases describe --database specflow --project pcb-inspect --format "value(pointInTimeRecoveryEnablement)"` | `POINT_IN_TIME_RECOVERY_ENABLED` |
| F02-RT-05 | `gcloud run services describe specflow-api --region us-central1 --project pcb-inspect --format yaml` | `timeoutSeconds: 300`, `containerConcurrency: 40`, imagem `@sha256:`, `startupProbe` em `/healthz` |
| F02-RT-06 | `curl -sI https://specsflow-ai.web.app` | CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy` |
| F02-RT-08 | `gcloud storage buckets describe gs://pcb-inspect-tfstate --format "value(versioning_enabled)"` | `True` |
| F02-RT-09 | revisar o `plan` do passo 2 | nenhum recurso fora de `specflow-*` / `specsflow-ai` |

## 6. LLM (F05, ADR-008)

Não há segredo de LLM: o Gemini é chamado no Vertex AI pela conta de serviço `specflow-api`
(`roles/aiplatform.user`). O Terraform ativa `aiplatform.googleapis.com` e configura `LLM_MODEL` e
`LLM_LOCATION` no Cloud Run (variáveis `llm_model`/`llm_location`). O segredo `specflow-llm-api-key`,
criado vazio na F02, foi removido.
