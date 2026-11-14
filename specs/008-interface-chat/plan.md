# F08 — Interface de chat em React — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- Rotas: `/chat` (redireciona para a última conversa ou nova), `/chat/:conversationId`, `/sobre`.
- `features/chat/`: `useChatStream(conversationId)` (estado do turno, abort, retry), `MessageList` (virtualizada se > 200 msgs),
  `Composer`, `ToolIndicator`, `ActionCard` (F06), `ConversationSidebar` (TanStack Query + mutações otimistas).
- Mocks MSW gerados a partir do OpenAPI permitem desenvolver em paralelo ao back.

### 9. Plano de testes
Unit/componente com MSW; E2E em preview do PR (smoke) e dev (completo).
