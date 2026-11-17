# F07 — Conversas persistentes — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · revisado em 2026-11-17 (T002 dividida em T002/T003; ≤ 1 d cada).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 6 tarefas · 5 d.

## 8. Tarefas

### Fase 1: Fundação

**Objetivo:** Persistência de conversas com paginação.

- [x] T001 Repositório: listar por cursor, histórico por cursor, exclusão em lotes — teste: `integration/test_conversations.py` — 1 d

---

### Fase 2: Incremento 1 — gestão de conversas

**Objetivo:** Criar, listar, abrir, renomear, excluir e fixar projeto.

**Aceitação:** AT-F07-01..05

- [x] T002 [F07-RF-01][F07-RF-02][F07-RF-05] Rotas de lista, criação, detalhe, renomear e excluir + contrato — teste: `test_conversations_api.py` — 1 d
- [x] T003 [F07-RF-03] Histórico paginado com ações embutidas e sem notas internas — teste: `test_conversations.py` — 0,5 d
- [x] T004 [F07-RF-04] Título automático em paralelo ao 1º turno — teste: `test_conversation_title.py` — 1 d
- [x] T005 [F07-RF-06] Projeto padrão no contexto do agente — teste: `test_chat_service.py` + eval `pinned_project_*` — 0,5 d

---

### Fase 3: Validação e entrega

**Objetivo:** Cenários de aceitação pela API (os de tela ficam com a F08).

**Aceitação:** AT-F07-01..05

- [ ] T006 AT-F07-01..05 pela API com o Gemini e o Jira sandbox — teste: `tests/acceptance/test_f07_conversations.py` — 1 d
