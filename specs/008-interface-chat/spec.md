# F08 — Interface de chat em React

| Campo | Valor |
|---|---|
| **Status** | Aceita |
| **Fase** | 2 — Produto |
| **Dependências** | F03 (pode iniciar com mocks), F05, F06, F07 |
| **ADRs** | ADR-002 |
| **Estimativa** | 9,5 dias |
| **Revisão** | 2026-11-17: ligada às APIs reais da F05–F07 — SSE com parser próprio, Markdown com `react-markdown` + `remark-gfm`, "Parar" grava a resposta parcial (RT-09), Lighthouse e tamanho do bundle sem previews de PR (ADR-006), relatório de erros do front movido para a F11 (F11-RT-11) |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** UI Streamlit limitada (container fixo de 400 px, CSS com classes internas `st-emotion-cache-*`, sem histórico, streaming falso).
- **Objetivo:** experiência de chat moderna, responsiva e acessível, com conversas na lateral, streaming real e cartões de ação.
- **Indicador:** tempo médio até a 1ª mensagem após login; erros de front (Error Reporting) < 0,5% das sessões.

### 2. Escopo
- **Inclui:** layout do app (sidebar com conversas, cabeçalho com usuário), página de chat, renderização Markdown,
  indicador de ferramentas, cartões de ação (de F06), estados vazio/erro/carregando, parar geração, copiar resposta,
  sugestões iniciais ("Escrever um épico", "Revisar backlog do projeto…"), página "Sobre", responsivo (≥ 360 px).
- **Inclui também (incremento 0, pedido do PO em 2026-11-14):** as telas principais do app antes do backend
  delas, para enxergar as funcionalidades: Chat, Projetos Jira (F09), Issues criadas (F10),
  Configurações › Jira (F04) e uso na Conta (F11). Cada tela fala com a interface `ProductApi`
  (`frontend/src/product/`); em produção ela devolve estados vazios até a feature dona ligar o endpoint
  real. Protótipo de referência: artefato "SpecFlow AI — Telas principais".
- **Fora de escopo:** editor de artefato (F14), tema escuro (backlog), i18n além de pt-BR. As regras de
  negócio das telas de F04, F09, F10 e F11 continuam nas specs delas.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F08-RF-01 | O usuário digita uma mensagem (Enter envia, Shift+Enter quebra linha) e vê a resposta surgir em streaming | Must |
| F08-RF-02 | Respostas renderizam Markdown (títulos, listas, tabelas, código com botão copiar) | Must |
| F08-RF-03 | Enquanto o agente usa ferramentas, aparece um indicador com a ação ("Consultando projetos no Jira…") | Should |
| F08-RF-04 | Propostas de ação aparecem como cartões confirmáveis no fluxo da conversa | Must |
| F08-RF-05 | A barra lateral lista conversas, permite criar, renomear e excluir | Must |
| F08-RF-06 | O usuário pode interromper uma resposta em andamento ("Parar"); a parte já recebida fica no histórico marcada como interrompida | Should |
| F08-RF-07 | Falhas de rede/servidor mostram mensagem clara com "Tentar novamente" sem perder o texto digitado | Must |
| F08-RF-08 | Uma conversa vazia mostra sugestões iniciais clicáveis | Could |
| F08-RF-09 | A interface funciona em celular (sidebar vira menu) | Must |
| F08-RF-10 | Um menu lateral leva às telas principais (Chat, Projetos Jira, Issues criadas, Configurações, Minha conta); enquanto a feature de uma tela não está no ar, ela mostra um estado vazio que explica o que vem | Must |
| F08-RF-11 | A raiz do site (`/`) é uma página inicial pública que apresenta o produto, o fluxo (conectar, conversar, confirmar) e o estágio do projeto, com chamadas para cadastro e login; quem já entrou vai direto para o chat. Exemplos de conversa são estáticos e marcados como ilustrativos | Should |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F08-RT-01 | Tipos do cliente gerados do OpenAPI; SSE por `fetch` + `ReadableStream` com parser próprio (`lib/sse.ts`), `Authorization` (token renovado em 401 antes do stream) e `AbortController` | contrato + unit |
| F08-RT-02 | Markdown com `react-markdown` + `remark-gfm`, sem HTML bruto (sem `rehype-raw`); links só `http(s)`/`mailto`, externos com `rel="noopener noreferrer"` | unit com payload XSS |
| F08-RT-03 | Lighthouse (mobile) em `/chat`: performance ≥ 85, acessibilidade ≥ 95 | Lighthouse local no build de produção (`vite preview`; sem previews de PR, ADR-006), registrado nas evidências |
| F08-RT-04 | axe sem violações sérias/críticas nas páginas do app | Playwright |
| F08-RT-05 | Bundle inicial ≤ 250 kB gzip (code splitting por rota se passar) | `scripts/check-bundle-size.mjs` no `postbuild` (falha o build e o CI) |
| F08-RT-06 | Renderização incremental eficiente: 5 mil tokens sem travar (≥ 50 fps no perfil) | teste de desempenho manual documentado |
| F08-RT-07 | ~~Erros de front reportados~~ — movido para a F11 (F11-RT-11) em 2026-11-17: depende do endpoint de log e do Error Reporting da observabilidade | — |
| F08-RT-08 | Dados de demonstração (`VITE_DEMO_DATA=true`) só em `npm run dev`; o build de produção não os contém e falha se contiver (`postbuild`: `scripts/check-no-demo.mjs`) | unit + build |
| F08-RT-09 | Cliente que desconecta no meio do turno ("Parar", aba fechada): o backend grava a resposta parcial com `interrupted: true`, e as ações já propostas continuam válidas | unit + integração |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Interface de chat

  Cenário: AT-F08-01 Enviar e ver streaming                     # F08-RF-01, F08-RF-02
    Dado que estou logado em uma conversa nova
    Quando envio "Liste 3 critérios de aceite para login em uma tabela"
    Então o texto da resposta cresce progressivamente
    E ao final vejo uma tabela renderizada

  Cenário: AT-F08-02 Indicador de ferramenta e cartão de ação   # F08-RF-03, F08-RF-04
    Quando peço uma task completa no projeto do Jira sandbox
    Então vejo o indicador da ferramenta durante o uso de ferramentas
    E vejo um cartão de ação com os botões de confirmar e recusar (sem confirmar: nada é escrito no Jira)

  Cenário: AT-F08-03 Gerenciar conversas na lateral             # F08-RF-05
    Quando crio uma conversa, renomeio para "Teste UI" e depois a excluo
    Então a lateral reflete cada mudança sem recarregar a página

  Cenário: AT-F08-04 Parar geração                              # F08-RF-06
    Quando envio um pedido longo e clico em "Parar" após o primeiro token
    Então o streaming para e a resposta parcial fica marcada como "interrompida"
    E ao recarregar a conversa a resposta parcial continua lá, marcada

  Cenário: AT-F08-05 Falha de rede preserva o texto             # F08-RF-07
    Dado que a API está indisponível (rota bloqueada no teste)
    Quando envio "Olá"
    Então vejo a mensagem de que não foi possível falar com o servidor e o botão "Try again"
    E o texto "Olá" continua disponível para reenvio

  Cenário: AT-F08-06 Uso em celular e acessibilidade            # F08-RF-09, F08-RT-04
    Dado a viewport de um celular (390x844)
    Então a lateral está recolhida em um menu
    E a verificação axe não encontra violações sérias

  Cenário: AT-F08-07 Telas principais sem dados inventados      # F08-RF-10, F08-RT-04, F08-RT-08
    Dado que estou logado no ambiente sem dados de demonstração
    Quando abro Chat, Projetos Jira, Issues criadas, Configurações e Minha conta pelo menu
    Então cada tela mostra o título e o estado vazio da sua feature
    E não aparece nenhum dado de demonstração
    E a verificação axe não encontra violações sérias
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| V Contrato | Cliente gerado |
| X UX/Acessibilidade | Streaming real, axe, Lighthouse, mensagens acionáveis |
| II Privacidade | Nenhum dado sensível em `localStorage` (só preferências de UI) |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F08-RF-01 | AT-F08-01 (`e2e/f08-chat.spec.ts`), `useChatStream.test.tsx`, `sse.test.ts`, `ChatPage.test.tsx` | ✅ |
| F08-RF-02 | AT-F08-01, `ChatMarkdown.test.tsx` | ✅ |
| F08-RF-03 | AT-F08-02 (`e2e/f08-chat-agente.spec.ts`), `ChatPage.test.tsx` | ✅ |
| F08-RF-04 | AT-F08-02, `ChatPage.test.tsx`, `screens.test.tsx` | ✅ |
| F08-RF-05 | AT-F08-03 (`e2e/f08-chat.spec.ts`), `ConversationSidebar.test.tsx`, `http.test.ts` | ✅ |
| F08-RF-06 | AT-F08-04 (`e2e/f08-chat-agente.spec.ts`), `useChatStream.test.tsx`, `ChatPage.test.tsx`, `test_chat_service.py` (RT-09) | ✅ |
| F08-RF-07 | AT-F08-05 (`e2e/f08-chat.spec.ts`), `useChatStream.test.tsx`, `ChatPage.test.tsx` | ✅ |
| F08-RF-08 | `screens.test.tsx` (sugestões e envio) | ✅ |
| F08-RF-09 | AT-F08-06 (`e2e/f08-chat.spec.ts`, `e2e/f08-telas.spec.ts`), `ConversationSidebar.test.tsx` | ✅ |
| F08-RF-10 | AT-F08-07 (`e2e/f08-telas.spec.ts`), `screens.test.tsx` | ✅ |
| F08-RF-11 | `LandingPage.test.tsx`, `e2e/f08-telas.spec.ts` (axe na página inicial) | ✅ |
| F08-RT-01 | `sse.test.ts`, `http.test.ts`, tipos de `openapi.json` | ✅ |
| F08-RT-02 | `ChatMarkdown.test.tsx` (XSS, links) | ✅ |
| F08-RT-03 | Lighthouse local (evidências) | ✅ |
| F08-RT-04 | `e2e/f08-chat.spec.ts`, `e2e/f08-telas.spec.ts` (axe) | ✅ |
| F08-RT-05 | `scripts/check-bundle-size.mjs` no `postbuild` | ✅ |
| F08-RT-06 | `blocks.test.ts`; medição manual `scripts/perf/` (evidências) | ✅ |
| F08-RT-08 | `screens.test.tsx` (F08-RT-08), `scripts/check-no-demo.mjs` no build | ✅ |
| F08-RT-09 | `test_chat_service.py`, `test_conversations.py`, AT-F08-04 | ✅ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
| 2026-11-17 | `feat/F08-interface-chat` | Local: Vite + API + emuladores, modelo de eco (`LLM_PROVIDER=fake`) | `E2E_EMULATORS=1 npx playwright test e2e/f08-chat.spec.ts e2e/f08-telas.spec.ts e2e/f03-auth.spec.ts` | 14/14: AT-F08-01 (streaming, Markdown com tabela, histórico ao recarregar), AT-F08-03, AT-F08-05, AT-F08-06 (axe sem violações sérias, 390×844 sem rolagem lateral), AT-F08-07 | PO (aceite com as evidências locais) |
| 2026-11-17 | `feat/F08-interface-chat` | Local: API + emuladores, Gemini `gemini-3.5-flash-lite` (Vertex, `pcb-inspect`), Jira sandbox `SCRUM` só leitura | `E2E_REAL_LLM=1 … e2e/f08-chat-agente.spec.ts` | 2/2: AT-F08-02 (indicador de ferramenta, cartão com Confirmar/Recusar, pendente após recarregar; nada confirmado, nada escrito no Jira), AT-F08-04 ("Stop" após o 1º token; parcial marcada como interrompida após recarregar) | PO (aceite com as evidências locais) |
| 2026-11-17 | `feat/F08-interface-chat` | Local: `npm run build` + `vite preview`, Lighthouse 12.8.2 mobile em `/chat/{id}` com histórico (Markdown, tabela, código) | `scripts/perf/lighthouse-chat.mjs`, 2 execuções | performance 92 e 93, acessibilidade 100, boas práticas 100; LCP 2,6–3,0 s, TBT 160–260 ms, CLS 0 | PO (aceite com as evidências locais) |
| 2026-11-17 | `feat/F08-interface-chat` | Local: build de produção, Chromium headless, 5000 tokens em ~11 s | `scripts/perf/stream-fps.mjs` | texto com parágrafos e listas: 60,1 fps, p95 do quadro 16,8 ms, 0 long tasks; pior caso (uma tabela única de ~625 linhas): 57,7 fps, p95 16,8 ms. Antes da divisão em blocos: 28,2 fps (corrigido) | PO (aceite com as evidências locais) |
| 2026-11-17 | `feat/F08-interface-chat` | Build de produção | `postbuild` | bundle inicial 218 kB gzip (limite 250 kB); sem dados de demonstração | PO (aceite com as evidências locais) |
