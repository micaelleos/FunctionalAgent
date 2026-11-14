# F02 — Infraestrutura base GCP/Firebase (Terraform) e pipeline de deploy — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- Bootstrap manual **único e documentado** (criar projetos, bucket de estado, billing) em `infra/bootstrap/README.md`;
  todo o resto por Terraform.
- `deploy.yml` conforme `06-cicd-deploy.md`. Canário: script que consulta métricas do Cloud Monitoring
  (`run.googleapis.com/request_count` por `response_code_class`) da tag `rc-<sha>`.
- `firestore.rules`: `match /{document=**} { allow read, write: if false; }`.
- **Rollback:** `update-traffic` para revisão anterior; `firebase hosting:rollback`.

### 7.1 Como foi implementado (2026-11-14, revisado após as decisões do PO)
- **Projeto compartilhado `pcb-inspect`, um ambiente só.** Terraform em `infra/terraform/` com
  `envs/prd.tfvars`/`envs/prd.backend.hcl` (estado em `gs://pcb-inspect-tfstate`, prefixo
  `specflow/prd`) e módulos `project_services`, `artifact_registry`, `firestore`, `secrets`, `kms`,
  `cloud_run`, `firebase`, `wif`. Tudo com prefixo `specflow`; região `us-central1`.
- **Fora do Terraform por desenho (F02-RT-09):** banco `(default)`, configuração de Auth/Identity
  Platform e orçamento, que são do projeto e compartilhados com os outros apps; valor do segredo do
  LLM; bucket de estado (bootstrap em `infra/bootstrap/README.md`).
- **Firestore:** banco nomeado `specflow` com PITR, backup diário (14 d), TTL de `pending_actions` e
  regras "nega tudo" publicadas pelo Terraform (`cloud.firestore/specflow`). O runtime só tem
  `datastore.user` com condição de IAM restrita a esse banco.
- **Hosting:** site `specsflow-ai`, criado pelo PO, importado (`import` em `main.tf`) e ligado ao web
  app `SpecFlow AI`; `firebase.json` fixa o site.
- **Cloud Run `specflow-api`:** o Terraform é dono da configuração (timeout, concorrência, probes,
  env, SA); a imagem e o tráfego pertencem ao pipeline (`ignore_changes`).
- **WIF `specflow-github`:** aceita só este repositório e os GitHub Environments `prd`/`preview` (SA
  `specflow-deployer`) e `infra-prd` (SA `specflow-terraform`). Nenhuma chave JSON.
- **Pipelines:** `deploy.yml` (build → aprovação `prd` → revisão sem tráfego + smoke → canário 10%
  por 15 min com `scripts/canary.py` → promoção ou rollback → frontend → AT em produção),
  `preview.yml` (tag `pr-<n>` + canal do Hosting; é a validação antes de produção), `infra.yml`
  (estático em todo PR; plan + apply em master com aprovação em `infra-prd`). Ações compostas em
  `.github/actions/`.
- **CORS:** `CORS_ORIGIN_REGEX` aceita só os canais de preview do próprio site (ADR-002).
- **Rollback:** automático no `deploy.yml`; manual e ensaio em `docs/runbooks/rollback.md`.

### 9. Plano de testes
| Camada | O que cobre |
|---|---|
| Estático | `terraform fmt/validate`, `tflint`, `actionlint` (infra.yml, CI) |
| Unitário | `scripts/test_canary.py` (decisão do canário, rollback ≤ 5 min), `backend/tests/unit/test_cors.py` |
| Regras | `infra/firestore-rules/firestore-rules.test.ts` no emulador (job `firestore-rules` do CI) |
| E2E / aceitação | AT-F02-01 e cabeçalhos F02-RT-06 em `frontend/e2e/f02-deploy.spec.ts` (deploy.yml, em produção); AT-F02-02/03 por execução do pipeline e ensaio do runbook |
| Infra real | checklist de `infra/bootstrap/README.md` §5 (F02-RT-01..09) |
