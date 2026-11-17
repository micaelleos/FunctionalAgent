# F08 — Interface de chat em React — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- **Rotas:** `/chat` (conversa nova; criada no 1º envio com `id=new`, ou por `POST /conversations` quando há projeto
  em `?projeto=`), `/chat/:conversationId`, `/about` (já existe).
- **`ProductApi`** (`product/`): `features.chat` ligado em `createHttpProductApi`.
  - `listConversations` → `GET /conversations?limit=50` (a lateral mostra as 50 mais recentes; "mais" é backlog).
  - `getMessages(id, cursor)` → página do histórico (`items`, `nextCursor`), carregada para cima.
  - `createConversation`, `renameConversation`, `pinProject`, `deleteConversation` → rotas da F07.
  - `streamMessage(conversationId | null, text, onEvent, signal)` → SSE da F05; devolve o id da conversa.
  - `ChatMessage` passa a ser `{id, role, text, actions, interrupted}` (o Markdown faz o resto).
- **SSE** (`lib/sse.ts`): `fetch` com `Authorization`; 401 renova o token e tenta de novo antes do stream; erro HTTP
  vira `ApiError` (Problem Details); o corpo é lido com `ReadableStream` e cada bloco `event:`/`data:` vira um
  evento tipado (`docs/api/sse-events.v1.json`). `AbortSignal` cancela. Quando a resposta abre, o cliente emite
  o evento local `open` com o `X-Conversation-Id`: a conversa nova vai para a URL antes do fim do turno, e "Parar"
  antes do `message_saved` não perde a resposta parcial.
- **`useChatStream`** (`chat/useChatStream.ts`): estado do turno (texto parcial, ferramenta em uso, ações propostas,
  erro, `interrupted`), `send`, `stop`, `retry`. O texto digitado só sai do campo quando o envio começa; erro antes do
  1º evento devolve o texto ao campo (RF-07). No `done`, invalida histórico, lista e uso e limpa o turno quando o
  histórico novo chega (sem piscar).
- **Componentes:** `ConversationSidebar` (criar, renomear inline, excluir com confirmação; mutações otimistas com
  rollback), `ChatMarkdown` (`react-markdown` + `remark-gfm`, sem HTML; tabelas com rolagem; código com "Copy
  code"), `StreamingMarkdown` (a resposta em andamento). Histórico, indicador de ferramenta (`role="status"`, o
  `summary` do `tool_start`) e campo de mensagem (Enter/Shift+Enter, "Stop" durante o turno) ficaram em
  `pages/ChatPage.tsx`; `ActionCard` (F06) sem mudanças. Rota única `/chat/:conversationId?`.
- **Backend (RT-09):** `ChatService._stream` captura o cancelamento do cliente (`CancelledError`), grava a resposta
  parcial com `interrupted: true` (protegida com `asyncio.shield`) e repassa o cancelamento; `MessageOut.interrupted`.
- **Desempenho (RT-06):** o texto em streaming acumula num `ref` e re-renderiza no máximo a cada quadro
  (`requestAnimationFrame`); acima de 8 mil caracteres, a cada 100 ms. `StreamingMarkdown` divide o texto em blocos
  (linha em branco fora de bloco de código, `chat/blocks.ts`) e só o último bloco é reprocessado; o histórico
  renderiza a mensagem inteira. Medição manual em `frontend/scripts/perf/` (sem os blocos: 28 fps).
- **Bundle (RT-05):** `scripts/check-bundle-size.mjs` no `postbuild` soma o gzip do JS e CSS de `index.html`;
  `React.lazy` por rota se passar de 250 kB.
- **Rollback:** `VITE_FEATURE_CHAT=false` no build volta a desligar o envio (o resto da tela continua).

### 9. Plano de testes
- Vitest + MSW: `sse.test.ts` (parser, blocos partidos, 401, erro HTTP, abort), `useChatStream.test.tsx`
  (streaming, parar, erro com texto preservado, retry), `ChatMarkdown.test.tsx` (tabela, código, XSS, links),
  `ConversationSidebar.test.tsx` (criar, renomear, excluir, otimista com rollback), `ChatPage.test.tsx`
  (ferramenta, cartão no fluxo, histórico paginado, interrompida).
- Backend: `test_chat_service.py` (cancelamento grava parcial), `test_conversations.py` (`interrupted` no histórico).
- E2E (Playwright): `e2e/f08-chat.spec.ts` (AT-F08-01, 03, 05, 06) contra a pilha local com o modelo de eco
  (`LLM_PROVIDER=fake`); `e2e/f08-chat-agente.spec.ts` (AT-F08-02, 04, com `E2E_REAL_LLM=1`) com o Gemini e o Jira
  sandbox só para leitura (nada é confirmado). Lighthouse local e o teste de 5 mil tokens registrados nas
  evidências.
