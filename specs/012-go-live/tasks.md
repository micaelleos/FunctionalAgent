# F12 — Go-live e desativação do Streamlit — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 4 tarefas · 3 d.

## 8. Tarefas

### Fase 1: Preparação

**Objetivo:** Prontidão e beta fechado.

- [ ] T001 Checklist de prontidão + beta — teste: revisão — 1 d

---

### Fase 2: Incremento 1 — migração dos usuários

**Objetivo:** Endereço antigo leva ao novo app; ajuda explica o novo fluxo.

**Aceitação:** AT-F12-02

- [ ] T002 [F12-RF-02][F12-RF-03] Redirecionamento + comunicação + página de ajuda — teste: AT-F12-02 — 0,5 d

---

### Fase 3: Validação e entrega

**Objetivo:** Paridade comprovada em prd e legado removido.

**Aceitação:** AT-F12-01

- [ ] T003 AT-F12-01 em prd; monitoramento — teste: Playwright — 0,5 d
- [ ] T004 Remoção do legado e atualização do README — teste: CI — 1 d
