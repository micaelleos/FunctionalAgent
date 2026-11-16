# F05 — API de chat com agente (LangGraph + streaming)

| Campo | Valor |
|---|---|
| **Status** | Rascunho |
| **Fase** | 1 — Núcleo |
| **Dependências** | F04 |
| **ADRs** | ADR-003, ADR-007 |
| **Estimativa** | 12 dias |
| **Revisão** | 2026-11-16: issues escritas para agentes de IA de código ([doc 10](../../docs/modernizacao/10-specs-para-agentes.md)) |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** agente em APIs descontinuadas, memória global compartilhada (D01), streaming falso (D13), ferramentas
  acopladas ao Streamlit com bugs (D05–D09, D11, D12).
- **Objetivo:** endpoint que conversa com o agente em streaming real, isolado por usuário e conversa, com ferramentas
  de leitura do Jira corrigidas e ferramentas de escrita que **apenas propõem** ações (execução em F06). As issues
  propostas são **specs prontas para agentes de IA de código** (Artigo XII, ADR-007): esquema estruturado, seções
  fixas e prontidão verificada.
- **Indicador:** primeiro token p75 ≤ 3 s; taxa de erro de turno < 2%; tokens/turno médios; % de propostas
  `agent-ready` (RA-42).

### 2. Escopo
- **Inclui:** grafo LangGraph, migração do `prompt_2` para `prompts/system_v1.md`, ferramentas da tabela em
  `03-arquitetura.md §3.2`, esquema `AgentReadySpec` e renderizador
  ADF/Markdown com seções fixas, verificação de prontidão (regras P-01 a P-10 do doc 10), conversor Markdown→ADF, SSE, persistência mínima das mensagens do turno
  (a gestão completa de conversas é F07), **baseline de evals gravado antes da migração**.
- **Fora de escopo:** UI (F08), confirmar/rejeitar ações (F06), listar/renomear conversas (F07).

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F05-RF-01 | O usuário envia uma mensagem e recebe a resposta do agente em streaming, token a token | Must |
| F05-RF-02 | O agente considera as mensagens anteriores **da mesma conversa e do mesmo usuário** | Must |
| F05-RF-03 | O agente consulta projetos, issues, issues de épico e buscas JQL do Jira do usuário | Must |
| F05-RF-04 | Quando o agente decide criar/atualizar um issue, gera uma **ação proposta** com prévia, sem escrever no Jira | Must |
| F05-RF-05 | Se o projeto não for informado nem inferível, o agente pergunta antes de propor a criação | Must |
| F05-RF-06 | O agente escreve histórias e tarefas no formato "spec pronta para agente" (seções fixas do doc 10 §4.2: objetivo, contexto, critérios de aceite em Gherkin com ID incluindo erro/borda, fora de escopo, como verificar) e épicos com objetivo, problema, benefícios, escopo, critérios e decomposição | Must |
| F05-RF-07 | Durante o uso de ferramentas o cliente recebe eventos de progresso ("Consultando o Jira…") | Should |
| F05-RF-08 | Se o usuário não tiver conexão Jira, o agente continua ajudando na documentação e avisa como conectar ao tentar usar o Jira | Must |
| F05-RF-09 | Quando falta informação para uma spec pronta (comportamento de erro, valores, textos exatos), o agente pergunta ao PO antes de propor; o que ficar sem resposta vai para "Perguntas em aberto" (RA-23) | Must |
| F05-RF-10 | Um pedido maior que um PR (mais de 8 critérios de aceite) vira um épico com histórias menores, cada uma com suas dependências (RA-10, RA-11) | Must |
| F05-RF-11 | O agente indica quando a mudança não é recomendada para agente de código (segurança, dados pessoais, autenticação, regra sem dono) e a proposta leva a label `human-only` (RA-24) | Should |
| F05-RF-12 | O PO pede "avalie a prontidão do ABC-12" e recebe o que falta, com uma proposta de atualização no formato do contrato (RA-25) | Should |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F05-RT-01 | Nenhum estado de conversa em memória global; agente montado por requisição com o `JiraClient` do usuário injetado | teste de concorrência: 2 usuários paralelos sem cruzamento |
| F05-RT-02 | Primeiro token p75 ≤ 3 s (excluindo latência do provedor acima do SLA) | métrica + teste de carga |
| F05-RT-03 | Limite de 8 iterações de ferramenta por turno; timeout de turno 240 s; erro amigável ao exceder | unit |
| F05-RT-04 | `buscar_issues_jql` limitado a 50 resultados com campos resumidos; descrições truncadas a 2 mil caracteres | unit |
| F05-RT-05 | Descrições enviadas ao Jira em ADF (API v3), convertidas de Markdown: títulos, listas, negrito/itálico, código, tabelas, links | unit com fixtures |
| F05-RT-06 | `parent` só é enviado quando informado (corrige D07); update só aceita `summary/description/priority/labels` (corrige D06) | unit |
| F05-RT-07 | Histórico: janela das últimas N mensagens até orçamento de tokens configurável; acima disso, sumarização persistida | unit |
| F05-RT-08 | Conteúdo vindo do Jira é delimitado como dado não confiável no contexto do modelo | revisão + eval de prompt injection |
| F05-RT-09 | Provedor/modelo/prompt configuráveis por env (`LLM_PROVIDER`, `LLM_MODEL`, `PROMPT_VERSION`); chave via Secret Manager (corrige D05) | unit de config |
| F05-RT-10 | Uso de tokens e custo estimado registrados por turno (log + `users/{uid}/usage/{dia}`) | integração |
| F05-RT-11 | Evals: baseline do agente atual gravado; nova implementação ≥ baseline em todas as métricas de F15 | `evals.yml` |
| F05-RT-12 | Eventos SSE seguem o esquema documentado em `03-arquitetura.md §3.5` (schema versionado e validado em teste de contrato) | contrato |
| F05-RT-13 | Ferramentas de escrita recebem `AgentReadySpec` (Pydantic, ADR-007); a descrição em ADF é renderizada do objeto com títulos e ordem fixos; o mesmo objeto gera o Markdown | unit com fixtures |
| F05-RT-14 | Verificação de prontidão é função pura sem LLM (P-01 a P-10), com termos vagos e limites versionados junto do prompt; o resultado vai no evento `action_proposed` | unit |
| F05-RT-15 | Labels da proposta: `specflow` sempre, `agent-ready` só se todas as regras obrigatórias passam, `human-only` quando indicado | unit |

### 5. Teste final de aceitação
Executado via API (`backend/tests/acceptance/test_f05_*.py`) contra dev com Jira sandbox e LLM real.
```gherkin
Funcionalidade: Conversa com o agente

  Cenário: AT-F05-01 Resposta em streaming                      # F05-RF-01, F05-RT-12
    Dado um usuário autenticado com uma conversa nova
    Quando envio "Olá, o que você faz?"
    Então recebo eventos "token" incrementais seguidos de "message_saved" e "done"
    E o primeiro "token" chega em menos de 3 segundos

  Cenário: AT-F05-02 Memória por conversa e isolamento         # F05-RF-02, F05-RT-01
    Dado que o usuário A disse "Meu produto se chama Zeta" na conversa A1
    Quando A pergunta "Qual o nome do meu produto?" na conversa A1
    Então a resposta contém "Zeta"
    Quando o usuário B pergunta "Qual o nome do meu produto?" na sua conversa
    Então a resposta não contém "Zeta"

  Cenário: AT-F05-03 Consulta ao Jira                           # F05-RF-03, F05-RF-07
    Dado que tenho conexão com o Jira sandbox
    Quando pergunto "Quais projetos eu tenho no Jira?"
    Então recebo os eventos "tool_start" e "tool_end" de "listar_projetos"
    E a resposta cita o projeto "E2E"

  Cenário: AT-F05-04 Criação vira spec pronta, proposta e sem escrita   # F05-RF-04, F05-RF-06, F05-RT-13, F05-RT-14
    Quando peço "Crie no projeto E2E uma story para login com e-mail e senha; senha errada mostra 'E-mail ou senha incorretos'"
    Então recebo um evento "action_proposed" do tipo "create_issue" com issuetype "Story"
    E a spec proposta tem as seções "Objetivo", "Contexto", "Critérios de aceite", "Fora de escopo" e "Como verificar"
    E há um critério "CA-0n" do tipo "erro" com o texto "E-mail ou senha incorretos"
    E a prontidão vem "pronta" com a label "agent-ready"
    E a quantidade de issues do projeto "E2E" no Jira não muda

  Cenário: AT-F05-05 Projeto não informado                     # F05-RF-05
    Quando peço "Crie uma story de logout"
    Então não recebo "action_proposed"
    E a resposta pede o projeto do Jira

  Cenário: AT-F05-06 Sem conexão Jira                           # F05-RF-08
    Dado um usuário sem conexão Jira
    Quando peço "Escreva um épico de onboarding"
    Então recebo o épico com objetivo, benefícios, escopo e critérios
    Quando peço "Envie ao Jira"
    Então a resposta orienta a conectar o Jira em Configurações

  Cenário: AT-F05-07 Falta informação: pergunta antes de propor # F05-RF-09
    Quando peço "Crie no E2E uma story de exportar relatório"
    Então não recebo "action_proposed"
    E a resposta pergunta pelo formato do arquivo e pelo comportamento quando não há dados

  Cenário: AT-F05-08 Pedido grande vira épico decomposto         # F05-RF-10
    Quando peço "Crie no E2E o módulo de assinaturas: planos, cobrança recorrente, cancelamento, troca de plano e notas fiscais"
    Então recebo uma proposta de épico com a seção "Decomposição"
    E propostas de histórias com no máximo 8 critérios de aceite cada

  Cenário: AT-F05-09 Mudança sensível marcada para humano       # F05-RF-11
    Quando peço "Crie no E2E uma story para trocar o algoritmo de hash das senhas"
    Então a proposta leva a label "human-only" e não leva "agent-ready"
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| II Privacidade | Agente sem estado global; histórico por `uid`/conversa |
| IV Humano no controle | Ferramentas de escrita só propõem |
| V Contrato | Esquema SSE versionado |
| IX Observabilidade | Tokens, custo e latência por turno |
| XI Qualidade do agente | Prompt versionado; ferramentas puras; evals |
| XII Specs para agentes | `AgentReadySpec`, seções fixas, prontidão verificada no código, perguntas antes de inventar |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F05-RF-01 | AT-F05-01 | ⬜ |
| F05-RF-02 | AT-F05-02 | ⬜ |
| F05-RF-03 | AT-F05-03 | ⬜ |
| F05-RF-04 | AT-F05-04, `test_tools_propose.py` | ⬜ |
| F05-RF-05 | AT-F05-05, eval `asks_project_*` | ⬜ |
| F05-RF-06 | AT-F05-04, AT-F05-06, `test_agent_ready_spec.py`, eval `contract_*` | ⬜ |
| F05-RF-07 | AT-F05-03 | ⬜ |
| F05-RF-08 | AT-F05-06 | ⬜ |
| F05-RF-09 | AT-F05-07, eval `asks_missing_*` | ⬜ |
| F05-RF-10 | AT-F05-08, eval `splits_large_*` | ⬜ |
| F05-RF-11 | AT-F05-09, eval `human_only_*` | ⬜ |
| F05-RF-12 | `test_readiness_review.py`, eval `review_existing_*` | ⬜ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
