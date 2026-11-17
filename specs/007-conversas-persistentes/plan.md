# F07 — Conversas persistentes — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- **API** (`api/v1/conversations.py`, `/api/v1`):
  - `GET /conversations?cursor=&limit=` → `{items: [ConversationOut], next_cursor}`, por `updatedAt desc`.
  - `POST /conversations {title?, project_key?}` → `201 ConversationOut`. `id=new` no envio de mensagem (F05) continua.
  - `GET /conversations/{id}` · `PATCH /conversations/{id} {title?, project_key?}` (`project_key: null` solta o
    projeto) · `DELETE /conversations/{id}` → `204`, idempotente (204 também se já não existe).
  - `GET /conversations/{id}/messages?cursor=&limit=` → `{items: [MessageOut], next_cursor}`: a página mais recente
    primeiro; dentro da página, da mais antiga para a mais nova; `next_cursor` leva às anteriores (o chat carrega
    para cima). Só `user` e `assistant`; `MessageOut.actions` traz o `ActionOut` (F06) de cada ação proposta.
  - `ConversationOut`: `id, title, project_key, created_at, updated_at, message_count`.
  - Cursor: base64url opaco de `(updatedAt ISO, id)` ou `(seq)`; inválido → 400 `invalid-cursor`. `limit` 1..50
    (padrão 20 na lista, 50 no histórico).
- **Dados:** `conversations/{id}` ganha `titleSource: "auto" | "user"`, `projectKey`. A mensagem do agente passa a
  guardar `text` (o que o usuário viu) além de `content` (com as notas "[Ação proposta …]" para o modelo); mensagens
  antigas sem `text` têm as notas removidas na leitura. Ordenação `updatedAt desc` usa o índice de campo único
  automático (sem mudança de infraestrutura).
- **Título (RT-05):** no 1º turno, `services/conversation_title.py` pede ao mesmo modelo um título de até 60
  caracteres em paralelo ao agente (`asyncio` dentro da requisição, para o Cloud Run não cortar a CPU) e grava antes
  do `done`, só se `titleSource` ainda for `auto`. Falha ou resposta vazia: fica o provisório. `AUTO_TITLE_ENABLED=false`
  desliga (custo ou rollback).
- **Projeto padrão (RF-06):** `project_note(key)` em `agent/graph.py` entra na instrução de sistema ("Projeto padrão
  desta conversa: SCRUM. Use-o sem perguntar, a menos que o usuário peça outro."). Formato da chave validado
  (`^[A-Z][A-Z0-9_]{1,9}$`); a existência no Jira é verificada pelo agente ao propor.
- **Exclusão (RT-03):** `ConversationService.delete` apaga mensagens em lotes, as ações da conversa e a conversa;
  ação em `executing` → 409 `conversation-busy` (o Jira pode estar gravando). `jira_issues` ficam (a issue existe no
  Jira); a F10 mostra a conversa como excluída. Confirmar uma ação de conversa excluída → 404 (já é o caso).
  `add_system_message` ignora conversa inexistente.
- **Camadas:** `api → services/conversations.py → repositories/conversations.py`; `ChatService` usa o título e a
  nota do projeto. Nada em `agent` conhece Firestore.
- **Front:** só os tipos (`api-schema.d.ts`) regenerados; a sidebar, o histórico e o projeto fixado na tela são F08.

### 9. Plano de testes
- Unit: `test_conversations.py` (serviço com o store em memória: CRUD, cursor, histórico sem notas, ações
  embutidas, exclusão, 409), `test_conversations_api.py` (rotas, 400/404/422, isolamento), `test_conversation_title.py`
  (título em paralelo, renomeado não é sobrescrito, falha mantém o provisório), `test_chat_service.py` (nota do
  projeto).
- Integração (emulador): paginação real, exclusão recursiva idempotente, `messageCount`/`updatedAt` no mesmo lote,
  desempenho da listagem com 500 conversas (p95 < 300 ms).
- Evals: casos `pinned_project_*` (projeto fixado → propõe nele sem perguntar), sem regressão nas demais.
- Aceitação AT-F07-01..05 (`tests/acceptance/test_f07_conversations.py`): API local + Gemini + Jira sandbox.
