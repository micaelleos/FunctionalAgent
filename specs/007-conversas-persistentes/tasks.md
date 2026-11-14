# F07 — Conversas persistentes — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 5 tarefas · 5 d.
**Dividir antes de implementar** (> 1 d, Art. I/VI): T002 (1,5 d).

## 8. Tarefas

### Fase 1: Fundação

**Objetivo:** Persistência de conversas com paginação.

- [ ] T001 Repositório + paginação por cursor — teste: integração — 1 d

---

### Fase 2: Incremento 1 — gestão de conversas

**Objetivo:** Criar, listar, abrir, renomear, excluir e fixar projeto.

**Aceitação:** AT-F07-01..05

- [ ] T002 [F07-RF-01][F07-RF-02][F07-RF-03][F07-RF-05] Rotas CRUD + histórico + contrato — teste: contrato — 1,5 d
- [ ] T003 [F07-RF-04] Título automático assíncrono — teste: integração — 1 d
- [ ] T004 [F07-RF-06] Projeto padrão no contexto do agente — teste: eval — 0,5 d

---

### Fase 3: Validação e entrega

**Objetivo:** Cenários de aceitação (os de UI dependem da F08).

**Aceitação:** AT-F07-01..05

- [ ] T005 AT-F07-01..05 (após F08 para os cenários de UI) — teste: Playwright — 1 d
