# F03 — Autenticação e conta do usuário — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

> Cada tarefa ≤ 1 dia e acompanhada do seu teste (Constituição, Art. I e VI).

### 8. Tarefas
| # | Tarefa | Teste | Est. |
|---|---|---|---|
| 1 | `current_user` + testes de autorização genéricos (matriz rota × token) | `test_authz_matrix.py` | 1 d |
| 2 | `/me` GET (cria perfil), export, DELETE | integração emulador | 1,5 d |
| 3 | AuthProvider, rotas protegidas, telas de login/cadastro/recuperar | Vitest + MSW | 1,5 d |
| 4 | Página "Conta" (exportar, excluir, sair) | AT-F03-04 | 0,5 d |
| 5 | E2E AT-F03-01..04 com emulador de Auth no CI e usuário de teste em dev | Playwright | 0,5 d |
