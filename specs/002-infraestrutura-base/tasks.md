# F02 — Infraestrutura base GCP/Firebase (Terraform) e deploy por `make deploy` — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · formato do `tasks-template` do projeto (checklist lido por
`/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 6 tarefas · 5 d. Escopo revisado em 2026-11-14 (ADR-006): o pipeline de CD saiu.

## 8. Tarefas

### Fase 1: Fundação

**Objetivo:** Recursos do app no projeto compartilhado, por Terraform.

- [x] T001 Bootstrap: bucket de estado e primeiro apply local — teste: checklist de `infra/bootstrap/README.md` — 0,5 d
- [x] T002 Módulos: services, artifact_registry, firestore, secrets, kms em infra/terraform/modules/ — teste: `terraform validate` + plan sem diffs — 1 d
- [x] T003 Módulos: cloud_run, firebase (web app + import do site) em infra/terraform/modules/ — teste: apply + plan sem diffs — 1 d

---

### Fase 2: Incremento 1 — publicação por `make deploy`

**Objetivo:** Um comando publica API e SPA com smoke antes do tráfego; rollback < 5 min.

**Aceitação:** AT-F02-01..04

- [x] T004 [F02-RT-04] `firebase.json` com headers, `firestore.rules`, índices — teste: AT-F02-04, teste de headers F02-RT-06 — 0,5 d
- [x] T005 [F02-RF-01][F02-RF-03] `make deploy` / `scripts/deploy.sh` e rota `/health` — teste: AT-F02-01 contra produção, `test_health.py` — 1 d
- [ ] T006 [F02-RF-02] Ensaio de smoke falho e rollback pelo runbook; remover o módulo `wif` do estado (`terraform apply`) — teste: AT-F02-02, AT-F02-03 — 0,5 d
