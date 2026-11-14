# F05 — API de chat com agente (LangGraph + streaming) — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

> Cada tarefa ≤ 1 dia e acompanhada do seu teste (Constituição, Art. I e VI).

### 8. Tarefas
| # | Tarefa | Teste | Est. |
|---|---|---|---|
| 1 | Dataset inicial de evals (30 casos) + baseline do agente legado | `evals/` | 1,5 d |
| 2 | Conversor Markdown→ADF | unit com fixtures | 1 d |
| 3 | Ferramentas de leitura e de proposta (com `pending_actions`) | unit com `JiraClient` fake | 2 d |
| 4 | Grafo LangGraph + prompt v1 + config de modelo | integração com LLM scripted | 1,5 d |
| 5 | Serviço de chat: histórico, janela/sumarização, persistência, uso | integração emulador | 1,5 d |
| 6 | Endpoint SSE + esquema de eventos + contrato | contrato | 1 d |
| 7 | Testes de aceitação AT-F05-01..06 + evals comparadas ao baseline | acceptance + evals | 1,5 d |
