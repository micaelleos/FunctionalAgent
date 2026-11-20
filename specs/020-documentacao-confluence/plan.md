# F20 — Documentação do projeto no Confluence — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Branch:** `feat/F20-documentacao-confluence` · **Data:** 2026-11-20 · **Status da spec:** Em implementação (revisada contra o código em 2026-11-20) · **ADRs:** ADR-009, ADR-003

## Parte B — Plano técnico (Gate 1)

### Resumo (Summary)
As ações propostas da F06 ganham três tipos novos (`create_space`, `create_page`, `update_page`). O agente monta o conteúdo em Markdown a partir dos modelos da metodologia. O
backend converte para storage format, calcula o diff e guarda tudo na proposta. A confirmação executa
exatamente o que foi visto, com a versão da página como trava contra sobrescrita.

### Contexto técnico (Technical Context)
| Item | Valor |
|---|---|
| **Agente** | Ferramentas `propor_*` novas em `agent/tools/confluence_tools.py`; `system_v2.md` (fase Convergir com escrita) |
| **Dados** | `users/{uid}/documents/{pageId}`; propostas na coleção de ações da F06 |
| **Integrações** | Confluence REST v2 (spaces, pages) + v1 (labels) |
| **Testes** | respx; emulador; Playwright no sandbox (AT-F20-01..05) |
| **Restrições** | ≤ 5 propostas de página/turno; página ≤ 50 mil caracteres |
| **Feature flag** | `CONFLUENCE_WRITE_ENABLED` (padrão `false`) |

### Conformidade com a Constituição (Constitution Check)
| Artigo | Verificação nesta feature | Status |
|---|---|---|
| IV Humano no controle | Execução só pela confirmação da F06; hash; versão; sem DELETE no cliente | ✅ |
| V Contrato primeiro | `kind` e payloads das ações novos na Fase 1; SSE `action_proposed` com `diff` | ✅ |
| VI Testes | respx, emulador, AT no sandbox | ✅ |
| VII Simplicidade | Reusa a máquina de ações propostas da F06 | ✅ |
| IX Observabilidade | `confluence_write` + painel | ✅ |
| XI Qualidade do agente | Evals de proposta de documentação (precisão e excesso) | ✅ |

### 7. Desenho
- **Fluxo:**
  1. a ferramenta `propor_*` valida os argumentos (tipo, título, pai, Markdown);
  2. o backend gera o storage format (F20-RT-03);
  3. para atualização, lê a página atual (versão N) e calcula o diff (F20-RT-04);
  4. grava a `ProposedAction` com payload, hash e `version = N`;
  5. a UI mostra o cartão com o diff;
  6. no Confirm, `confluence_actions.execute` confere o hash e faz `PUT` com `version.number = N + 1`.
     Um 409 vira `confluence-version-conflict` e a ação fica `failed`;
  7. acrescenta a linha no "Registro de mudanças" (outro `PUT`, com a versão lida na hora; se ele falhar, a
     ação principal fica `done` com aviso);
  8. grava `users/{uid}/documents/{pageId}` e o log `confluence_write`.
- **Criação do espaço:** `POST /wiki/rest/api/space` (`key`, `name`), depois as páginas do modelo em ordem
  (pai antes do filho) e os rótulos; por fim o vínculo do projeto. Falha no meio: a ação fica `failed` com o
  código `confluence-partial`, a lista do que foi criado e o link. Nunca se apaga o que já foi criado (sem DELETE).
- **Contrato:**
  - payloads das ações (`kind`, `spaceId`, `parentId`, `title`, `storage`, `labels`, `pageId`, `version`, `diff`);
  - `GET /api/v1/documents?project=` para a aba "Docs";
  - Problem Details: `confluence-version-conflict`, `confluence-forbidden`, `confluence-space-key-taken`.
- **Modelos:** `docs/metodologia/modelos/*.md` copiados para `backend/app/agent/templates/confluence/`; um
  teste confere que estão iguais (F20-RT-05).
- **Infra:** a variável `CONFLUENCE_WRITE_ENABLED`.

### 9. Plano de testes
| Camada | O que cobre |
|---|---|
| Unitário | cliente de escrita (201, 409, 403, sem retry); Markdown ↔ storage; diff; hash; limites; ADR aceita não editável |
| Integração | confirmação da F06 executando ações `confluence.*` com cliente fake; repositório de documentos |
| E2E / aceitação | AT-F20-01..05 no Confluence do sandbox (pede aprovação do PO antes de rodar, como no Jira) |
| Evals | `confluence-converge-write-*`, `confluence-adr-*`, `confluence-no-spam-*` (não propor página sem motivo) |

### Riscos e rollback
| Risco | Mitigação |
|---|---|
| Sobrescrever edição humana | Versão da página na proposta; 409 recusa |
| Agente propõe páginas demais | Limite por turno; evals de excesso; propostas descartáveis |
| Criação do espaço parcial | Estado `partial` com o que foi criado; nova proposta completa o que falta |
| Formato do storage quebrar a página | Conversor determinístico e testado; macros mínimas |

**Rollback:** `CONFLUENCE_WRITE_ENABLED=false`. As ferramentas `propor_*` somem do agente e as páginas
já escritas ficam no Confluence (o histórico de versões do próprio Confluence permite voltar cada uma).

### Gate 1 — Plano aprovado
- [x] Contrato definido antes do código
- [x] Riscos e rollback descritos
- [x] Estimativa cabe na Fase 4 (6 d)
- [x] Conformidade sem exceção
