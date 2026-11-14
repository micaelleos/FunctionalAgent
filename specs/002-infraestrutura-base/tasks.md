# F02 — Infraestrutura base GCP/Firebase (Terraform) e pipeline de deploy — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 6 tarefas · 7 d.
**Dividir antes de implementar** (> 1 d, Art. I/VI): T002 (1,5 d), T003 (1,5 d), T005 (2 d).

## 8. Tarefas

### Fase 1: Fundação

**Objetivo:** Projetos GCP e módulos Terraform base.

- [ ] T001 Bootstrap: bucket de estado, primeiro apply, GitHub — teste: checklist — 0,5 d (roteiro pronto em `infra/bootstrap/README.md`; execução manual pendente)
- [ ] T002 Módulos: services, artifact_registry, firestore, secrets, kms em infra/terraform/modules/ — teste: `terraform validate` + plan — 1,5 d (validate/tflint ok; falta plan com credenciais)
- [ ] T003 Módulos: cloud_run, firebase (web app + import do site), wif em infra/terraform/modules/ — teste: plan/apply — 1,5 d (código pronto; budget e Auth saíram do escopo, F02-RT-07/09; falta apply)

---

### Fase 2: Incremento 1 — publicação automatizada

**Objetivo:** Merge publica em dev; prd com aprovação, canário e rollback; previews por PR.

**Aceitação:** AT-F02-01..04

- [ ] T004 [F02-RT-04] `firebase.json` com headers, `firestore.rules`, índices — teste: AT-F02-04, teste de headers — 0,5 d (AT-F02-04 verde no emulador; teste de headers aguarda o Hosting publicado)
- [ ] T005 [F02-RF-01][F02-RF-02][F02-RF-03] `deploy.yml` (dev, prd com aprovação, canário, rollback) + scripts/canary.py — teste: AT-F02-01..03 — 2 d (sem estágio dev, por decisão do PO; workflow e canário prontos; AT-F02-01 verde localmente; falta rodar no pipeline)
- [ ] T006 [F02-RF-04] `preview.yml` + `infra.yml` — teste: PR de prova — 1 d (workflows prontos; falta PR de prova após o bootstrap)
