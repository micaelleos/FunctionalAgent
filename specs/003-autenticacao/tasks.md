# F03 — Autenticação e conta do usuário — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 5 tarefas · 5 d.
**Dividir antes de implementar** (> 1 d, Art. I/VI): T002 (1,5 d), T003 (1,5 d).

## 8. Tarefas

### Fase 1: Fundação

**Objetivo:** Autorização genérica por token para todas as rotas.

**Aceitação:** AT-F03-03

- [ ] T001 `current_user` + testes de autorização genéricos (matriz rota × token) — teste: `test_authz_matrix.py` — 1 d

---

### Fase 2: Incremento 1 — conta no backend

**Objetivo:** Perfil criado no primeiro acesso; exportar e excluir dados.

**Aceitação:** AT-F03-02, AT-F03-04

- [ ] T002 [F03-RF-05][F03-RF-07][F03-RF-08] `/me` GET (cria perfil), export, DELETE — teste: integração com emulador — 1,5 d

---

### Fase 3: Incremento 2 — login e conta na interface

**Objetivo:** Login Google/e-mail, rotas protegidas, página Conta.

**Aceitação:** AT-F03-01, AT-F03-02, AT-F03-04

- [ ] T003 [P] [F03-RF-01][F03-RF-02][F03-RF-03][F03-RF-04] AuthProvider, rotas protegidas, telas de login/cadastro/recuperar senha — teste: Vitest + MSW — 1,5 d
- [ ] T004 [F03-RF-06][F03-RF-07][F03-RF-08] Página "Conta" (exportar, excluir, sair) — teste: AT-F03-04 — 0,5 d

---

### Fase 4: Validação e entrega

**Objetivo:** Cenários de aceitação automatizados.

**Aceitação:** AT-F03-01..04

- [ ] T005 E2E AT-F03-01..04 com emulador de Auth no CI e usuário de teste em dev — teste: Playwright — 0,5 d
