# F10 — Histórico de issues criados — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- **Registro (F06, `services/actions.py`):** `_done` grava a ação concluída e o registro da issue num único batch
  (`ActionRepository.complete_action`). Criação: `{key, url, projectKey, issueType, summary, labels, actionId,
  conversationId, createdAt, operation: "created"}` (como hoje). Atualização: merge com `lastActionId`,
  `updatedAt`, `summary`/`labels` se mudaram e, se a issue ainda não estava no histórico, `createdAt`,
  `operation: "updated"`, `projectKey` (prefixo da chave) e `issueType`.
- **Leitura (`repositories/jira_issues.py`):** `list_issues(uid, after, before_date, from_date, limit)` ordenado por
  `createdAt desc, __name__ desc`; `get_issue`; `clear_conversation(uid, conversation_id)` (chamado pela exclusão da
  F07); títulos das conversas por `get_all`.
- **Serviço (`services/jira_issues.py`, `JiraIssueService`):** lista paginada com filtros (projeto, tipo, prontidão em
  memória, período na consulta) lendo em lotes de 100 até encher a página ou 1000 lidos; `statuses(keys)` numa JQL;
  `agent_prompt(key)` a partir da ação mais recente com `payload.spec`.
- **API (`api/v1/jira_issues.py`):** `GET /api/v1/jira/issues?project=&type=&readiness=&from=&to=&cursor=&limit=`
  → `{items: [{key, url, project_key, issue_type, summary, readiness, operation, created_at, updated_at,
  conversation_id, conversation_title}], next_cursor}`; `POST /api/v1/jira/issues/status` `{keys}` →
  `{statuses: {KEY: "To Do" | null}}`; `GET /api/v1/jira/issues/{key}/agent-prompt` → `{text}`.
- **Front:** `ProductApi.listIssues(filters, cursor)`, `issueStatuses(keys)`, `agentPrompt(key)`; `IssuesPage` com
  filtros enviados à API (os projetos do filtro vêm da F09), "Load more", selo de prontidão, "Copy for coding agent",
  status por "Refresh Jira status".

### 9. Plano de testes
- Backend: `test_jira_issues.py` (registro em batch na criação e na atualização, filtros, cursor, período, prontidão,
  conversa excluída, status por JQL com issue apagada, agent-prompt e 404) com fakes; repositório no emulador
  (`tests/integration`).
- Front: `IssuesPage.test.tsx`, `http.test.ts`.
- E2E (`e2e/f10-historico.spec.ts`): AT-F10-01..04 com issue criada no sandbox pela API (confirmação explícita) —
  **escreve no Jira**: roda só com a autorização do PO.

### Rollback
Reverter o merge: a tela volta ao estado vazio. Os registros já existiam desde a F06; os campos novos são aditivos.
