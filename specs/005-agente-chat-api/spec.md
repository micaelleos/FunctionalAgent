# F05 — API de chat com agente (LangGraph + streaming)

| Campo | Valor |
|---|---|
| **Status** | Rascunho |
| **Fase** | 1 — Núcleo |
| **Dependências** | F04 |
| **ADRs** | ADR-003 |
| **Estimativa** | 10 dias |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** agente em APIs descontinuadas, memória global compartilhada (D01), streaming falso (D13), ferramentas
  acopladas ao Streamlit com bugs (D05–D09, D11, D12).
- **Objetivo:** endpoint que conversa com o agente em streaming real, isolado por usuário e conversa, com ferramentas
  de leitura do Jira corrigidas e ferramentas de escrita que **apenas propõem** ações (execução em F06).
- **Indicador:** primeiro token p75 ≤ 3 s; taxa de erro de turno < 2%; tokens/turno médios.

### 2. Escopo
- **Inclui:** grafo LangGraph, migração do `prompt_2` para `prompts/system_v1.md`, ferramentas da tabela em
  `03-arquitetura.md §3.2`, conversor Markdown→ADF, SSE, persistência mínima das mensagens do turno
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
| F05-RF-06 | O agente escreve stories em BDD (cenários, critérios de aceite, cenários de teste) e épicos com objetivo, benefício, escopo e critérios | Must |
| F05-RF-07 | Durante o uso de ferramentas o cliente recebe eventos de progresso ("Consultando o Jira…") | Should |
| F05-RF-08 | Se o usuário não tiver conexão Jira, o agente continua ajudando na documentação e avisa como conectar ao tentar usar o Jira | Must |

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
| F05-RT-12 | Eventos SSE seguem o esquema documentado em `03-arquitetura.md §3.4` (schema versionado e validado em teste de contrato) | contrato |

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

  Cenário: AT-F05-04 Criação vira ação proposta, sem escrita   # F05-RF-04, F05-RF-06
    Quando peço "Crie no projeto E2E uma story para login com e-mail e senha"
    Então recebo um evento "action_proposed" do tipo "create_issue" com issuetype "Story"
    E a descrição proposta contém "Cenário" e "Critérios de aceite"
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
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| II Privacidade | Agente sem estado global; histórico por `uid`/conversa |
| IV Humano no controle | Ferramentas de escrita só propõem |
| V Contrato | Esquema SSE versionado |
| IX Observabilidade | Tokens, custo e latência por turno |
| XI Qualidade do agente | Prompt versionado; ferramentas puras; evals |

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
| F05-RF-06 | AT-F05-04, AT-F05-06, eval `bdd_format_*` | ⬜ |
| F05-RF-07 | AT-F05-03 | ⬜ |
| F05-RF-08 | AT-F05-06 | ⬜ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
