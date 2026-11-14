# F11 — Observabilidade, limites de uso e proteção — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 5 tarefas · 5 d.
**Dividir antes de implementar** (> 1 d, Art. I/VI): T003 (1,5 d).

## 8. Tarefas

### Fase 1: Fundação

**Objetivo:** Telemetria e proteção da API.

**Aceitação:** AT-F11-04

- [ ] T001 Logging/tracing/métricas — teste: testes de log — 1 d
- [ ] T002 [P] App Check (front + back) — teste: integração — 0,5 d

---

### Fase 2: Incremento 1 — limites de uso

**Objetivo:** Consumo visível, cota diária e rate limit com mensagens claras.

**Aceitação:** AT-F11-01, AT-F11-02

- [ ] T003 [F11-RF-01][F11-RF-02][F11-RF-03] Cotas + rate limit + UI de consumo — teste: integração/Vitest — 1,5 d

---

### Fase 3: Incremento 2 — alertas

**Objetivo:** Responsável alertado em erro, latência, falhas externas e orçamento.

**Aceitação:** AT-F11-03

- [ ] T004 [F11-RF-04] Dashboard, alertas, SLOs (Terraform) — teste: AT-F11-03 — 1 d

---

### Fase 4: Validação e entrega

**Objetivo:** Carga, segurança e operação.

- [ ] T005 Teste de carga, varredura ZAP, runbooks — teste: k6/ZAP — 1 d
