# F08 — Interface de chat em React — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 13 tarefas · 9.5 d. Incremento 0 (T007–T010) incluído em 2026-11-14 a 2026-11-16 a pedido do PO;
revisado em 2026-11-17 (T002 e T006 divididas; T011–T013).

## 8. Tarefas

### Fase 0: Incremento 0 — telas principais com dados de demonstração

**Objetivo:** Ver as telas do produto antes do backend de F04–F11, sem levar dados falsos à produção.

**Aceitação:** AT-F08-07

- [x] T007 [F08-RF-10][F08-RF-09] `AppLayout` (menu lateral, gaveta no celular, uso e estado do Jira), rotas `/chat/:id`, `/projetos`, `/issues`, `/configuracoes` — teste: `screens.test.tsx`, `e2e/f08-telas.spec.ts` — 1 d
- [x] T008 [F08-RF-10][F08-RT-08] `ProductApi` (`unavailable` em produção, `demo` só em `npm run dev:demo`) e telas Projetos, Issues, Configurações › Jira e uso na Conta — teste: `screens.test.tsx`, `check-no-demo.mjs` — 1 d
- [x] T009 [F08-RF-04][F08-RF-08] Chat: lista de conversas, sugestões, mensagens, `ActionCard` com confirmar/rejeitar, Enter/Shift+Enter, texto preservado em erro — teste: `screens.test.tsx` — 1 d
- [x] T010 [F08-RF-11] Página inicial pública em `/` (produto, fluxo, estágio, cadastro/login); logado vai para o chat — teste: `LandingPage.test.tsx`, axe em `e2e/f08-telas.spec.ts` — 0.5 d

---

### Fase 1: Incremento 1 — conversas na lateral

**Objetivo:** Lateral ligada à API de F07.

**Aceitação:** AT-F08-03, AT-F08-06

- [x] T001 [F08-RF-05] `ConversationSidebar` ligada à F07: criar, renomear e excluir com mutações otimistas (layout e menu responsivo já feitos em T007) — teste: `ConversationSidebar.test.tsx` — 0,5 d

---

### Fase 2: Incremento 2 — conversa

**Objetivo:** Streaming, Markdown seguro, ferramentas, cartões e estados de erro.

**Aceitação:** AT-F08-01, AT-F08-02, AT-F08-04, AT-F08-05

- [x] T002 [F08-RF-01] Cliente SSE (`lib/sse.ts`) e `ProductApi` do chat ligada às rotas da F05/F07 — teste: `sse.test.ts`, `http.test.ts` — 1 d
- [x] T011 [F08-RF-06][F08-RF-07] `useChatStream`: turno em andamento, parar, erro com texto preservado, tentar de novo — teste: `useChatStream.test.tsx` — 1 d
- [x] T012 [F08-RF-06] Backend grava a resposta parcial ao desconectar (`interrupted`) — teste: `test_chat_service.py` — 0,5 d
- [x] T003 [P] [F08-RF-02] `ChatMarkdown` seguro + copiar código — teste: `ChatMarkdown.test.tsx` (XSS) — 0,5 d
- [x] T004 [F08-RF-03][F08-RF-04] Tela do chat: histórico paginado, indicador de ferramenta, cartões no fluxo — teste: `ChatPage.test.tsx` — 1 d
- [x] T005 [P] [F08-RF-07][F08-RF-08] Estados vazio/erro e sugestões ligados ao envio real — teste: `ChatPage.test.tsx` — 0,5 d

---

### Fase 3: Validação e entrega

**Objetivo:** Aceitação, desempenho e tamanho do bundle.

**Aceitação:** AT-F08-01..06

- [x] T013 [P] Tamanho do bundle no `postbuild` e teste de 5 mil tokens — teste: `check-bundle-size.mjs`, perfil manual — 0,5 d
- [x] T006 E2E AT-F08-01..06 contra a pilha local e Lighthouse local — teste: `e2e/f08-chat.spec.ts`, `e2e/f08-chat-agente.spec.ts` — 1 d
