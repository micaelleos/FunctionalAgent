# F04 — Conexão Jira por usuário — Tarefas

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

**Objetivo:** Cifra de credenciais e cliente Jira reutilizável (usado por F05, F09, F10).

- [ ] T001 `Cipher` KMS/local + testes — teste: unit + integração com KMS em dev — 1 d
- [ ] T002 `JiraClient` (myself, projects, issue, search, create, update) com respx — teste: unit — 1,5 d

---

### Fase 2: Incremento 1 — conexão Jira

**Objetivo:** O usuário cadastra, valida, troca e remove a conexão; token nunca volta ao navegador.

**Aceitação:** AT-F04-01..05

- [ ] T003 [F04-RF-01][F04-RF-02][F04-RF-03][F04-RF-04][F04-RF-05][F04-RF-06] Serviço + rotas + matriz de autorização — teste: integração — 1 d
- [ ] T004 [P] [F04-RF-01][F04-RF-03][F04-RF-04][F04-RF-05][F04-RF-06][F04-RF-07] Tela de configuração + banner de reconexão — teste: Vitest + MSW — 1 d

---

### Fase 3: Validação e entrega

**Objetivo:** Cenários de aceitação contra o Jira sandbox.

**Aceitação:** AT-F04-01..05

- [ ] T005 E2E AT-F04-01..05 contra Jira sandbox — teste: Playwright — 0,5 d
