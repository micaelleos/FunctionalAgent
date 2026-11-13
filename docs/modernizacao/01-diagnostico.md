# 01 — Diagnóstico do estado atual

## 1. Visão geral

| Item | Situação atual |
|---|---|
| Tipo de app | Streamlit multipágina (`main.py` + `pages/*.py`) |
| Tamanho | ~710 linhas Python em 9 arquivos |
| Agente | LangChain `AgentExecutor` com OpenAI Functions, `ChatOpenAI` (modelo padrão) |
| Integração | `atlassian-python-api` com usuário + API token do Jira Cloud |
| Persistência | Nenhuma — tudo em `st.session_state` / `st.cache_resource` |
| Autenticação | Nenhuma |
| Testes / CI / IaC | Nenhum |
| Deploy | Manual (`Makefile` só para Windows) |

### Funcionalidades existentes (a preservar)

1. **Chat com o agente** para criar documentação funcional (épicos, stories em BDD, tasks) — `pages/chat_page.py`.
2. **Ferramentas do agente no Jira** — `src/scripts/tools_jira.py`:
   `criar_issue_jira`, `get_all_projects`, `consultar_issue`, `atualizar_issue_jira`, `consultar_jql_query`
   (`consultar_issues_within_epic` existe mas está desativada).
3. **Lista de projetos Jira** do usuário com contagem de issues — `pages/projects_list_page.py`.
4. **Lista de issues criados na sessão** com link para o Jira — `pages/issues_list_page.py`.
5. **Página "Sobre"** com instruções de uso e de geração de API token — `pages/sobre_page.py`.
6. **Prompt de sistema** de PO assistente (`prompt_2`) — `src/scripts/prompt.py`. É o principal ativo
   intelectual do app e deve ser migrado e versionado.

## 2. Problemas encontrados

Classificação: **C** = crítico (segurança/privacidade ou bloqueia multiusuário) · **A** = alto (bug funcional) ·
**M** = médio (manutenção/qualidade).

| # | Sev. | Problema | Onde | Consequência | Resolvido em |
|---|---|---|---|---|---|
| D01 | **C** | Memória do chat criada com `@st.cache_resource` é **global ao processo**: todos os usuários compartilham o mesmo histórico | `pages/chat_page.py:67` | Usuário B vê/influencia a conversa do usuário A (vazamento de dados) | F05, F07 |
| D02 | **C** | Credenciais do Jira em texto puro em `st.session_state`; campo "API Key" sem `type="password"` | `pages/chat_page.py:39`, `pages/projects_list_page.py:33` | Token exposto na tela; sem rotação nem criptografia | F04 |
| D03 | **C** | Sem autenticação: qualquer pessoa com a URL usa a chave OpenAI do dono | `main.py` | Custo ilimitado, abuso | F03, F11 |
| D04 | **C** | Agente escreve no Jira só com base no prompt ("pergunte antes") — nada no código impede a escrita sem confirmação; conteúdo lido do Jira pode conter *prompt injection* | `src/scripts/tools_jira.py` | Issues criados/alterados sem consentimento | F06 |
| D05 | A | Variável de ambiente `OPEN_API_KEY` (código) ≠ `OPENAI_API_KEY` (README) | `pages/chat_page.py:58` | Falha de configuração silenciosa | F05 |
| D06 | A | `atualizar_issue_jira` envia `project` e `issuetype` em update (Jira rejeita mover projeto por update) e a docstring diz "criar issues" | `src/scripts/tools_jira.py:99` | Atualizações falham ou o LLM escolhe a ferramenta errada | F05 |
| D07 | A | `parent: {"key": None}` enviado quando não há issue pai | `src/scripts/tools_jira.py:33` | Erro na criação de issues sem pai em alguns tipos de projeto | F05 |
| D08 | A | Descrição em Markdown enviada à API v2 (que espera *wiki markup*) | `src/scripts/tools_jira.py` | Formatação quebrada no Jira | F05 (conversor Markdown→ADF, API v3) |
| D09 | A | `consultar_jql_query` pagina **todos** os resultados sem limite | `src/scripts/tools_jira.py:165` | Estouro de contexto/tokens e latência | F05 |
| D10 | A | Issues criados ficam só na sessão; link `…{url}browse/{key}` depende da URL terminar com `/` | `src/scripts/tools_jira.py:42`, `pages/issues_list_page.py:27` | Histórico perdido no refresh; links quebrados | F10 |
| D11 | M | Ferramentas acopladas ao Streamlit (`import streamlit` dentro de `tools_jira.py`) | `src/scripts/tools_jira.py` | Impossível testar ou reutilizar fora da UI | F05 |
| D12 | M | APIs do LangChain descontinuadas (`format_tool_to_openai_function`, `langchain.chat_models.ChatOpenAI`, `ConversationBufferMemory`, `AgentExecutor`) | `pages/chat_page.py`, `src/scripts/llm_openai.py` | Quebra em upgrades; sem streaming real | F05 (LangGraph) |
| D13 | M | Streaming simulado com `time.sleep` palavra por palavra | `pages/chat_page.py:78` | Usuário espera a resposta inteira e depois uma animação falsa | F05, F08 |
| D14 | M | Contagem de issues: uma chamada ao Jira por projeto (N+1) a cada render | `pages/projects_list_page.py:20` | Página lenta, risco de rate limit | F09 |
| D15 | M | Código morto: `llm_openai.py`, `tools.py` (com bug de tuplas por vírgula final em `self.url= …,` linhas 23/28), `prompt_1` | `src/scripts/` | Confusão e manutenção | F01 |
| D16 | M | `__pycache__/*.pyc` versionados; `python-dotenv` usado mas fora do `requirements.txt`; dependências sem versão | raiz | Builds não reprodutíveis | F01 |
| D17 | M | Erros retornados como string com `print`, sem logging estruturado | todo o backend | Sem diagnóstico em produção | F11 |
| D18 | M | README cita `app.py` e um `LICENSE` que não existem; `Makefile` só funciona no Windows | raiz | Onboarding confuso | F01 |

## 3. O que se aproveita

- **Prompt de sistema `prompt_2`** → migra para `backend/app/agent/prompts/system_v1.md`, versionado e coberto por evals (F15).
- **Esquemas Pydantic das ferramentas** (`IssueJira`, `ConsultaIssue`, `JQLjiraQuery` …) → base dos contratos das novas ferramentas.
- **Fluxos de UI** (chat, projetos, issues, sobre) → viram as rotas do React.
- **Logos** em `src/img/` → movidos para `frontend/public/`.

## 4. Recomendação imediata (opcional, antes da migração)

Se o Streamlit estiver publicado hoje para outras pessoas, aplicar um *hotfix* de 1 linha para o D01
(trocar `@st.cache_resource` por memória em `st.session_state`) e restringir o acesso até o go-live (F12).
O restante dos problemas é resolvido pela nova arquitetura, não por correções no código legado.
