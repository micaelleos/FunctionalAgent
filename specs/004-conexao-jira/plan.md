# F04 — Conexão Jira por usuário — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- **API:** `GET/POST /api/v1/jira/connections`, `PUT /{id}/token`, `DELETE /{id}`, `POST /{id}/validate`.
  Request `POST`: `{siteUrl, email, apiToken}`; response: `{id, siteUrl, email, accountName, tokenHint, status, lastValidatedAt}`.
- **Back:** `core/crypto.py` (`Cipher` protocolo: `KmsCipher`, `LocalFernetCipher`), `integrations/jira/client.py`
  (`JiraClient` async com Basic auth), `services/jira_connections.py`, `repositories/jira_connections.py`.
  Fábrica `get_jira_client(uid)` usada por F05/F09/F10.
- **Front:** `/configuracoes/jira` com React Hook Form + Zod; banner global de "reconectar" quando a API retorna
  `code=jira_auth_invalid`.
- **Rollback:** revisão anterior; dados aditivos.

### 9. Plano de testes
Teste de redação de logs: injeta token conhecido, executa fluxo, varre logs capturados → zero ocorrências.
