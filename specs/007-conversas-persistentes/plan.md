# F07 — Conversas persistentes — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- **API:** `GET /conversations?cursor=`, `POST /conversations {title?, projectKey?}`, `GET/PATCH/DELETE /conversations/{id}`,
  `GET /conversations/{id}/messages?cursor=` (mensagens + ações embutidas por `actionId`).
- **Back:** `repositories/conversations.py`, `services/conversations.py`; injeção de `projectKey` no prompt de sistema
  ("Projeto padrão desta conversa: E2E").
- **Front:** consumido na F08 (sidebar).

### 9. Plano de testes
Integração com emulador; desempenho de listagem com 500 conversas sintéticas.
