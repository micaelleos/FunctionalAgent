# F08 — Interface de chat em React — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 6 tarefas · 7 d.
**Dividir antes de implementar** (> 1 d, Art. I/VI): T001 (1,5 d), T002 (2 d), T006 (1,5 d).

## 8. Tarefas

### Fase 1: Incremento 1 — estrutura da interface

**Objetivo:** Layout, navegação e barra lateral responsiva.

**Aceitação:** AT-F08-03, AT-F08-06

- [ ] T001 [F08-RF-05][F08-RF-09] Layout, navegação, sidebar responsiva — teste: Vitest — 1,5 d

---

### Fase 2: Incremento 2 — conversa

**Objetivo:** Streaming, Markdown seguro, ferramentas, cartões e estados de erro.

**Aceitação:** AT-F08-01, AT-F08-02, AT-F08-04, AT-F08-05

- [ ] T002 [F08-RF-01][F08-RF-06][F08-RF-07] `useChatStream` + Composer + streaming + abort/retry — teste: unit com SSE mock — 2 d
- [ ] T003 [P] [F08-RF-02] Markdown seguro + copiar código — teste: unit de XSS — 0,5 d
- [ ] T004 [F08-RF-03][F08-RF-04] Integração ActionCard + ToolIndicator — teste: Vitest — 1 d
- [ ] T005 [P] [F08-RF-07][F08-RF-08] Estados vazio/erro, sugestões, página Sobre — teste: Vitest — 0,5 d

---

### Fase 3: Validação e entrega

**Objetivo:** Aceitação, desempenho e tamanho do bundle.

**Aceitação:** AT-F08-01..06

- [ ] T006 E2E AT-F08-01..06, Lighthouse CI, size-limit — teste: Playwright — 1,5 d
