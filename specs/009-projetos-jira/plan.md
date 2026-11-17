# F09 — Projetos Jira — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- **Cliente Jira** (`integrations/jira/client.py`): `list_projects(*, insight=False, max_pages=20)` pagina
  `project/search` (`startAt`, `maxResults=50`) até `isLast`; com `insight` traz `totalIssueCount`, `id` e o avatar
  48×48. `approximate_count(jql) -> int` (`POST /rest/api/3/search/approximate-count`). A ferramenta
  `listar_projetos` do agente continua lendo só a 1ª página (até 50, sem `insight`).
- **Serviço** (`services/jira_projects.py`, `JiraProjectService`): conexão do usuário → cache → Jira. Contagem de
  abertas com `asyncio.Semaphore(5)`; falha de uma contagem vira `None`. Erros conforme F09-RT-05; 401/403 chama
  `JiraConnectionService.mark_invalid`.
- **Cache** (`repositories/jira_cache.py`): documento `users/{uid}/cache/jiraProjects`
  `{connectionId, siteUrl, fetchedAt, projects}`; vale 5 min e só para a mesma conexão e site.
- **API** (`api/v1/jira_projects.py`): `GET /api/v1/jira/projects?refresh=false` →
  `{items: [{id, key, name, type, avatar_url, open_issues|null, total_issues|null, url}], fetched_at}`.
- **Front**: `ProductApi.listProjects(refresh?)` ligado em `createHttpProductApi`; `features.projects: true`.
  `ProjectsPage`: avatar com reserva de iniciais (`onError`), "—" para contagem nula, botão "Refresh", erro de
  credencial com link para Configurações. Tipos regenerados (`make api-types`).

### 9. Plano de testes
- Backend unit (`test_jira_projects.py`, `test_jira_client.py`): paginação e teto, `insight`, approximate-count,
  concorrência ≤ 5, falha de contagem → `None`, cache (acerto, expirado, outra conexão, `refresh`), erros
  (sem conexão, 401 → inválida, fora do ar), URL `/browse/KEY`; p95 com Jira falso de 200 ms por chamada.
- Front (`ProjectsPage.test.tsx`, `http.test.ts`): cards, "—", filtro, links, "Chat about this project",
  reserva de avatar, "Refresh", erro de credencial.
- E2E (`e2e/f09-projetos.spec.ts`): AT-F09-01..03 contra a pilha local e o Jira sandbox (só leitura).

### Rollback
Reverter o merge: a tela volta ao estado vazio (`features.projects: false`). O cache no Firestore é descartável.
