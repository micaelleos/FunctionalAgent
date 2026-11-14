# F02 — Infraestrutura base GCP/Firebase (Terraform) e pipeline de deploy — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

> Cada tarefa ≤ 1 dia e acompanhada do seu teste (Constituição, Art. I e VI).

### 8. Tarefas
| # | Tarefa | Teste | Est. |
|---|---|---|---|
| 1 | Bootstrap: projetos, billing, bucket de estado | checklist | 0,5 d |
| 2 | Módulos: services, artifact_registry, firestore, secrets, kms | `terraform validate` + plan | 1,5 d |
| 3 | Módulos: cloud_run, firebase (hosting, auth), wif, budget | plan/apply dev | 1,5 d |
| 4 | `firebase.json` com headers, `firestore.rules`, índices | AT-F02-04, teste de headers | 0,5 d |
| 5 | `deploy.yml` (dev, prd com aprovação, canário, rollback) | AT-F02-01..03 | 2 d |
| 6 | `preview.yml` + `infra.yml` | PR de prova | 1 d |
