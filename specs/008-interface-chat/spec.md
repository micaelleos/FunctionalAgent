# F08 — Interface de chat em React

| Campo | Valor |
|---|---|
| **Status** | Em implementação |
| **Fase** | 2 — Produto |
| **Dependências** | F03 (pode iniciar com mocks), F05, F06, F07 |
| **ADRs** | ADR-002 |
| **Estimativa** | 9,5 dias |

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
| F08-RF-06 | O usuário pode interromper uma resposta em andamento ("Parar") | Should |
| F08-RF-07 | Falhas de rede/servidor mostram mensagem clara com "Tentar novamente" sem perder o texto digitado | Must |
| F08-RF-08 | Uma conversa vazia mostra sugestões iniciais clicáveis | Could |
| F08-RF-09 | A interface funciona em celular (sidebar vira menu) | Must |
| F08-RF-10 | Um menu lateral leva às telas principais (Chat, Projetos Jira, Issues criadas, Configurações, Minha conta); enquanto a feature de uma tela não está no ar, ela mostra um estado vazio que explica o que vem | Must |
| F08-RF-11 | A raiz do site (`/`) é uma página inicial pública que apresenta o produto, o fluxo (conectar, conversar, confirmar) e o estágio do projeto, com chamadas para cadastro e login; quem já entrou vai direto para o chat. Exemplos de conversa são estáticos e marcados como ilustrativos | Should |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F08-RT-01 | Cliente API gerado do OpenAPI; SSE via `fetch-event-source` com `Authorization` e `AbortController` | contrato + unit |
| F08-RT-02 | Markdown sanitizado (sem HTML bruto); links externos com `rel="noopener noreferrer"` | unit com payload XSS |
| F08-RT-03 | Lighthouse (mobile) em `/chat`: performance ≥ 85, acessibilidade ≥ 95 | CI (lighthouse-ci) em preview |
| F08-RT-04 | axe sem violações sérias/críticas nas páginas do app | Playwright |
| F08-RT-05 | Bundle inicial ≤ 250 kB gzip (code splitting por rota) | `size-limit` no CI |
| F08-RT-06 | Renderização incremental eficiente: 5 mil tokens sem travar (≥ 50 fps no perfil) | teste de desempenho manual documentado |
| F08-RT-07 | Erros de front reportados (Error Reporting via endpoint de log do backend ou Sentry — decidir no plano) | integração |
| F08-RT-08 | Dados de demonstração (`VITE_DEMO_DATA=true`) só em `npm run dev`; o build de produção não os contém e falha se contiver (`postbuild`: `scripts/check-no-demo.mjs`) | unit + build |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Interface de chat

  Cenário: AT-F08-01 Enviar e ver streaming                     # F08-RF-01, F08-RF-02
    Dado que estou logado em uma conversa nova
    Quando envio "Liste 3 critérios de aceite para login em uma tabela"
    Então o texto da resposta cresce progressivamente
    E ao final vejo uma tabela renderizada

  Cenário: AT-F08-02 Indicador de ferramenta e cartão de ação   # F08-RF-03, F08-RF-04
    Quando peço "Crie uma task no E2E para revisar textos"
    Então vejo "Consultando…" durante o uso de ferramentas
    E vejo um cartão de ação com botões "Confirmar" e "Recusar"

  Cenário: AT-F08-03 Gerenciar conversas na lateral             # F08-RF-05
    Quando crio uma conversa, renomeio para "Teste UI" e depois a excluo
    Então a lateral reflete cada mudança sem recarregar a página

  Cenário: AT-F08-04 Parar geração                              # F08-RF-06
    Quando envio um pedido longo e clico em "Parar" após o primeiro token
    Então o streaming para e a resposta parcial fica marcada como "interrompida"

  Cenário: AT-F08-05 Falha de rede preserva o texto             # F08-RF-07
    Dado que a API está indisponível (rota bloqueada no teste)
    Quando envio "Olá"
    Então vejo "Não foi possível falar com o servidor" e o botão "Tentar novamente"
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
| F08-RF-01 | AT-F08-01 | ⬜ |
| F08-RF-02 | AT-F08-01 | ⬜ |
| F08-RF-03 | AT-F08-02 | ⬜ |
| F08-RF-04 | AT-F08-02 | ⬜ |
| F08-RF-05 | AT-F08-03 | ⬜ |
| F08-RF-06 | AT-F08-04 | ⬜ |
| F08-RF-07 | AT-F08-05 | ⬜ |
| F08-RF-08 | `screens.test.tsx` (sugestões) | 🟡 sem agente real |
| F08-RF-09 | AT-F08-06 (`e2e/f08-telas.spec.ts`, menu em celular), `screens.test.tsx` | 🟡 menu pronto |
| F08-RF-10 | AT-F08-07 (`e2e/f08-telas.spec.ts`), `screens.test.tsx` | ✅ |
| F08-RF-11 | `LandingPage.test.tsx`, `e2e/f08-telas.spec.ts` (axe na página inicial) | ✅ |
| F08-RT-08 | `screens.test.tsx` (F08-RT-08), `scripts/check-no-demo.mjs` no build | ✅ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
