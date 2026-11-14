# F04 — Conexão Jira por usuário — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

> Cada tarefa ≤ 1 dia e acompanhada do seu teste (Constituição, Art. I e VI).

### 8. Tarefas
| # | Tarefa | Teste | Est. |
|---|---|---|---|
| 1 | `Cipher` KMS/local + testes | unit + integração KMS em dev | 1 d |
| 2 | `JiraClient` (myself, projects, issue, search, create, update) com respx | unit | 1,5 d |
| 3 | Serviço + rotas + matriz de autorização | integração | 1 d |
| 4 | Tela de configuração + banner de reconexão | Vitest + MSW | 1 d |
| 5 | E2E AT-F04-01..05 contra Jira sandbox | Playwright | 0,5 d |
