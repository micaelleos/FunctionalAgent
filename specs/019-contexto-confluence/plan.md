# F19 — Contexto do Confluence e metodologia em fases no agente — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Branch:** `feat/F19-contexto-confluence` · **Data:** 2026-11-20 · **Status da spec:** Em implementação · **ADRs:** ADR-009

## Parte B — Plano técnico (Gate 1)

### Resumo (Summary)
Cada projeto Jira ganha um vínculo com um espaço do Confluence do mesmo site Atlassian, descoberto
automaticamente e confirmado pelo usuário. O agente ganha três ferramentas de leitura restritas ao espaço
e um prompt v2 com as 7 fases da metodologia. A `AgentReadySpec` v2 ganha "Referências" e os conflitos
declarados pelo modelo, validados no código contra as páginas lidas no turno. Não há escrita no
Confluence (F20).

### Contexto técnico (Technical Context)
| Item | Valor |
|---|---|
| **Backend** | Python 3.12, FastAPI, Pydantic v2, uv |
| **Frontend** | React 19 + TypeScript strict, Vite, TanStack Query |
| **Agente** | LangGraph com Gemini no Vertex AI; `system_v2.md`; ferramentas novas em `agent/tools/confluence_tools.py` |
| **Dados** | Firestore `users/{uid}/project_links/{projectKey}` |
| **Integrações** | Confluence Cloud REST v2 (`/wiki/api/v2`: spaces, pages, children) + v1 para busca CQL (`/wiki/rest/api/search`) e rótulos; httpx |
| **Testes** | pytest + respx + emuladores; Vitest + MSW; Playwright (AT-F19-01, -03, -05 com o LLM de eco/roteirizado); evals com espaço fake |
| **Metas de desempenho** | Fase Descobrir ≤ 4 s no p95 (4 leituras em paralelo); primeiro token p75 ≤ 3 s continua valendo depois da descoberta |
| **Restrições** | ≤ 6 páginas/turno, ≤ 10 resultados/busca, 8 mil caracteres/página, índice ≤ 30 itens (F19-RT-04) |
| **Feature flag** | `CONFLUENCE_ENABLED` (padrão `false` até o aceite) e `PROMPT_VERSION` (já existe; `v1`/`v2`) |

### Conformidade com a Constituição (Constitution Check)
| Artigo | Verificação nesta feature | Status |
|---|---|---|
| I Spec antes do código | Spec com AT-F19-01..05 para todo RF Must | ✅ |
| II Privacidade | Vínculo sob `users/{uid}`; nenhuma página persistida; credencial do usuário | ✅ |
| III Segredos | Reusa `JiraConnectionService.client_for` (token KMS); nada novo | ✅ |
| IV Humano no controle | Só leitura; vínculo após clique | ✅ |
| V Contrato primeiro | Rotas da F19-RT-08 e esquema v2 na Fase 1 | ✅ |
| VI Testes | Testes por RF; AT em Playwright; evals | ✅ |
| VII Simplicidade | Sem infra nova (ADR-009) | ✅ |
| VIII IaC | Só variáveis de ambiente novas no módulo `cloud_run` | ✅ |
| IX Observabilidade | `confluence_read` + métrica + painel; indicador da spec §1 | ✅ |
| X UX e acessibilidade | Textos da UI em inglês (padrão do app), anúncio de progresso em `aria-live` | ✅ |
| XI Qualidade do agente | `system_v2.md`; ferramentas puras; evals v2 ≥ v1 | ✅ |
| XII Specs para agentes | Esquema v2 com `references`; P-10 mantida; XII.5 emendado (PATCH) | ✅ |

### 7. Desenho
- **Componentes afetados:**
  - `integrations/confluence/` (`client.py`, `markdown.py`);
  - `services/confluence_links.py` (descoberta e vínculo);
  - `services/confluence_reader.py` (adaptador);
  - `repositories/project_links.py`;
  - `agent/tools/confluence_tools.py`, `agent/tools/context.py` (`ConfluenceReader`), `agent/spec/schema.py` (v2),
    `render.py`, `agent/prompts/system_v2.md`;
  - `services/chat.py`: monta o `ConfluenceReader` quando há vínculo;
  - `api/v1/confluence.py`;
  - frontend: `ProjectsPage` (cartão do espaço), `ChatPage` (aviso de conflito na proposta), `product/http.ts`.
- **Contrato de API:**
  - `GET /api/v1/jira/projects/{key}/confluence` → `{link: Link | null, suggestion: Space | null}`;
  - `PUT /api/v1/jira/projects/{key}/confluence` → body `{space_key}`, devolve `Link`; antes, valida
    `GET /wiki/api/v2/spaces?keys=`;
  - `DELETE` → 204;
  - `GET /api/v1/confluence/spaces?q=` → `[{id, key, name, url}]`, no máximo 25;
  - erros: `confluence-forbidden` (403 do Confluence), `confluence-space-not-found`, `jira-not-connected`;
  - SSE: o evento `tool_progress` já existente ganha os textos das ferramentas novas; o evento
    `action_proposed` ganha `conflicts[]`. A versão do schema SSE sobe (`docs/api/sse-events.v1.json` →
    campo opcional, sem quebra).
- **Dados (Firestore):** `users/{uid}/project_links/{projectKey}`, com os campos de F19-RT-07. Sem índice novo.
- **Infra:** variáveis `CONFLUENCE_ENABLED` e `PROMPT_VERSION` no Cloud Run (Terraform). Nada mais.
- **Decisões:**
  - Descoberta: primeiro `GET /wiki/api/v2/spaces?keys=<KEY>`; depois CQL
    `label = "specflow-projeto-<key>" AND type = page`. A descoberta roda ao abrir o projeto e no 1º turno
    com o projeto fixado; o resultado só aparece como sugestão.
  - Fase Descobrir: a cada turno com o projeto da conversa vinculado, o código monta o **índice** do espaço
    (páginas do modelo por rótulo `specflow-tipo-*` ou título; títulos das ADRs; ≤ 30 itens, uma busca CQL)
    e o injeta na instrução de sistema, delimitado como não confiável. O prompt v2 manda ler as páginas fixas
    antes da primeira proposta. Injetar as páginas inteiras custaria até 20 mil tokens por turno, contra a
    cota diária de 200 mil.
  - Conflitos: o modelo os declara, e o código filtra pelos IDs vistos (`RN-\d{2}`, `ADR-\d{3}`,
    `Art\. [IVX]+`) nas páginas lidas no turno.

### Estrutura (Project Structure)
```text
specs/019-contexto-confluence/{spec,plan,tasks}.md
backend/app/
├── api/v1/confluence.py
├── services/{confluence_links,confluence_reader}.py, chat.py
├── agent/tools/{confluence_tools,context}.py
├── agent/spec/{schema,render}.py
├── agent/prompts/system_v2.md
├── integrations/confluence/{client,markdown,errors}.py
└── repositories/project_links.py
backend/tests/{unit,integration,contract}/…confluence…
evals/datasets/confluence-*, evals/datasets/confluence_space/
frontend/src/pages/{ProjectsPage,ChatPage}.tsx, frontend/src/product/{http,demo,types}.ts
frontend/e2e/f19-confluence.spec.ts
infra/terraform/modules/cloud_run/main.tf
```

### 9. Plano de testes
| Camada | O que cobre |
|---|---|
| Unitário | cliente (respx: auth, 403, 404, retries, sem redirect); Markdown (macros, tabelas); CQL escapada; limites; esquema v2 + hash; filtro de conflitos |
| Integração | vínculo no emulador; `ChatService` com `ConfluenceReader` fake (descoberta, sem acesso) |
| Contrato | rotas `/api/v1/…/confluence`; SSE `conflicts` opcional |
| E2E / aceitação | AT-F19-01, -03, -05 no Playwright (Confluence fake no backend local); AT-F19-02 e -04 no sandbox (roteiro manual) |
| Evals | `confluence-context-*`, `confluence-clarify-*`, `confluence-conflict-*`, `confluence-injection-*`, `confluence-converge-*`; v2 ≥ v1 |

### Riscos e rollback
| Risco | Mitigação |
|---|---|
| Injeção de prompt via página | Tag de não confiável, regra no prompt, evals de injeção, propostas sempre confirmadas (Art. IV) |
| Latência da fase Descobrir | Leituras em paralelo, cache por turno, só no 1º turno da conversa |
| Custo de tokens (páginas grandes) | Truncagem em 8 mil caracteres; conta na cota diária e no teto mensal (F11/F12) |
| Token sem acesso ao Confluence | F19-RF-09: segue sem documentação e avisa |
| Esquema v2 quebra propostas antigas | `references` opcional; specs v1 continuam válidas; hash da v1 inalterado quando a lista está vazia |

**Rollback:** `CONFLUENCE_ENABLED=false` e `PROMPT_VERSION=v1` (`gcloud run services update`, < 1 min).
Os vínculos ficam no Firestore e não são usados.

### Gate 1 — Plano aprovado
- [x] Contrato da API definido antes do código
- [x] Riscos e plano de rollback descritos
- [x] Estimativa cabe na Fase 4 (6 d)
- [x] Conformidade com a Constituição sem exceção
