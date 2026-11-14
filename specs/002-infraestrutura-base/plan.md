# F02 — Infraestrutura base GCP/Firebase (Terraform) e deploy por `make deploy` — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- Bootstrap manual **único e documentado** (bucket de estado, primeiro apply) em
  `infra/bootstrap/README.md`; todos os recursos do app por Terraform, aplicado localmente.
- Deploy por `make deploy` (`scripts/deploy.sh`, ADR-006), com o login do gcloud do dono do produto.
- `firestore.rules`: `match /{document=**} { allow read, write: if false; }`.
- **Rollback:** `update-traffic` para revisão anterior; `firebase hosting:rollback`.

### 7.1 Como foi implementado (2026-11-14, revisado após as decisões do PO)
- **Projeto compartilhado `pcb-inspect`, um ambiente só.**
  - Terraform em `infra/terraform/`, com `envs/prd.tfvars` e `envs/prd.backend.hcl`.
  - Estado em `gs://pcb-inspect-tfstate`, prefixo `specflow/prd`.
  - Módulos `project_services`, `artifact_registry`, `firestore`, `secrets`, `kms`, `cloud_run` e
    `firebase`.
  - Tudo com prefixo `specflow`; região `us-central1`.
- **Fora do Terraform por desenho (F02-RT-09):**
  - banco `(default)`, configuração de Auth/Identity Platform e orçamento, que são do projeto e
    compartilhados com os outros apps;
  - valor do segredo do LLM;
  - bucket de estado (bootstrap).
- **Firestore:**
  - banco nomeado `specflow`, com PITR, backup diário (14 d) e TTL de `pending_actions`;
  - regras "nega tudo" publicadas pelo Terraform (`cloud.firestore/specflow`);
  - o runtime só tem `datastore.user`, com condição de IAM restrita a esse banco.
- **Hosting:** site `specsflow-ai`, criado pelo PO, importado (`import` em `main.tf`) e ligado ao web
  app `SpecFlow AI`; `firebase.json` fixa o site.
- **Cloud Run `specflow-api`:** o Terraform é dono da configuração (timeout, concorrência, probes, env,
  SA). A imagem e o tráfego pertencem ao `make deploy` (`ignore_changes`). `template.revision` não é
  ignorado e fica vazio.
- **`make deploy`:**
  - `deploy-api`, pela API v2 do Cloud Run, sem `gcloud run deploy`:
    1. cria a imagem com `APP_VERSION=<sha>[-dirty]` e envia ao Artifact Registry (uma versão por
       deploy, sem atestação);
    2. cria a revisão sem tráfego, com a tag `rc-<versão>`, e fixa o tráfego na revisão atual;
    3. faz o smoke em `<tag>/health`;
    4. passa 100% do tráfego para "latest" e remove a tag. Se o smoke falhar, o tráfego continua na
       revisão anterior.
  - Por que a API v2: o `gcloud run deploy` dá nome às revisões (`template.revision`), e com o nome
    fixado qualquer mudança de configuração pelo Terraform falha com 409. Pela API v2 o nome fica
    vazio e o Cloud Run o gera.
  - Por que "latest": uma revisão criada pelo Terraform também passa a servir.
  - `deploy-web`: cria o SPA com `VITE_API_BASE_URL` igual à URL do Cloud Run e roda
    `firebase deploy --only hosting`, que exige ADC.
- **`/health` × `/healthz`:** o front-end do Google devolve 404 para `/healthz` nas URLs `*.run.app`
  (caminho reservado). A API expõe as duas rotas: `/healthz` atende as probes do contêiner e `/health`
  atende os clientes externos (SPA, smoke, E2E).
- **Artifact Registry:** a limpeza mantém as 3 imagens mais recentes (a revisão no ar e o rollback)
  e apaga o resto depois de 1 dia.
- **CI:** o job `terraform` do `ci.yml` roda `fmt`, `validate` e `tflint` sem credenciais.
- **Removido em 2026-11-14 (ADR-006):**
  - `deploy.yml`, `preview.yml`, `infra.yml` e `.github/actions/`;
  - `scripts/canary.py`;
  - o módulo `wif` (pool, provider e as SAs `specflow-deployer` e `specflow-terraform`);
  - `CORS_ORIGIN_REGEX`.

### 9. Plano de testes
| Camada | O que cobre |
|---|---|
| Estático | `terraform fmt/validate`, `tflint` (job `terraform` do CI, `make infra-check`) |
| Unitário | `backend/tests/unit/test_health.py` (`/health` e `/healthz`), `backend/tests/unit/test_cors.py` |
| Regras | `infra/firestore-rules/firestore-rules.test.ts` no emulador (job `firestore-rules` do CI) |
| E2E / aceitação | AT-F02-01 e cabeçalhos F02-RT-06 em `frontend/e2e/f02-deploy.spec.ts`, com `E2E_BASE_URL=https://specsflow-ai.web.app` após o `make deploy`; AT-F02-02/03 por ensaio do runbook |
| Infra real | checklist de `infra/bootstrap/README.md` (F02-RT-01..09) |
