# F09 — Projetos Jira — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico
### 7. Desenho
`GET /api/v1/jira/projects` → `[{id, key, name, avatarUrl, typeKey, issueCount|null, url}]`. Página `/projetos` com grid responsivo.
### 9. Plano de testes
respx para a API do Jira; E2E com sandbox.
