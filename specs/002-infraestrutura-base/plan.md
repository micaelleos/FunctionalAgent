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

### 7.1 Como foi implementado (2026-11-14)
- **Terraform** em `infra/terraform/`: um módulo raiz por ambiente (`envs/<env>.tfvars` +
  `envs/<env>.backend.hcl`) e módulos `project_services`, `artifact_registry`, `firestore`,
  `secrets`, `kms`, `cloud_run`, `firebase`, `wif`, `budget`. Região `us-central1`.
- **Cloud Run:** o Terraform é dono da configuração (timeout, concorrência, probes, env, SA); a
  imagem e o tráfego pertencem ao pipeline (`ignore_changes`). Imagem inicial pública `hello`.
- **Regras do Firestore** publicadas pelo Terraform (`google_firebaserules_release`) a partir de
  `firestore.rules`; PITR e backup diário só em prd.
- **WIF:** o provider aceita só este repositório e os GitHub Environments `<env>` (SA `deployer@`)
  e `infra-<env>` (SA `terraform@`). Nenhuma chave JSON.
- **Pipelines:** `deploy.yml` (build único → dev 100% → AT em dev → aprovação `prd` → revisão sem
  tráfego → canário 10% por 15 min com `scripts/canary.py` → promoção ou rollback), `preview.yml`
  (tag `pr-<n>` + canal do Hosting, limpeza ao fechar o PR), `infra.yml` (estático em todo PR,
  plan de dev comentado, apply em master com aprovação em `infra-prd`). Ações compostas em
  `.github/actions/`.
- **CORS:** `CORS_ORIGIN_REGEX` aceita os canais de preview do próprio site (ADR-002).
- **Fora do Terraform por desenho:** valor do segredo do LLM; criação dos projetos, faturamento e
  bucket de estado (bootstrap em `infra/bootstrap/README.md`).
- **Rollback:** automático no `deploy.yml`; manual e ensaio em `docs/runbooks/rollback.md`.

### 9. Plano de testes
| Camada | O que cobre |
|---|---|
| Estático | `terraform fmt/validate`, `tflint`, `actionlint` (infra.yml, CI) |
| Unitário | `scripts/test_canary.py` (decisão do canário, rollback ≤ 5 min), `backend/tests/unit/test_cors.py` |
| Regras | `infra/firestore-rules/firestore-rules.test.ts` no emulador (job `firestore-rules` do CI) |
| E2E / aceitação | AT-F02-01 e cabeçalhos F02-RT-06 em `frontend/e2e/f02-deploy.spec.ts` (deploy.yml, dev e prd); AT-F02-02/03 por execução do pipeline e ensaio do runbook |
| Infra real | checklist de `infra/bootstrap/README.md` §5 (F02-RT-01..08) |
