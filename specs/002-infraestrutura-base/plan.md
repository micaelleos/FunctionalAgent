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

### 9. Plano de testes
Terraform: `fmt`, `validate`, `tflint`, `plan` no PR. Regras Firestore: `@firebase/rules-unit-testing`. E2E: AT-F02-01..04.
