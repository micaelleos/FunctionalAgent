<!-- Template de plano do projeto (substitui o plan-template do Spec Kit).
     Preenchido por /speckit-plan a partir de spec.md e da Constituição. Mantém as seções que o
     comando espera (Resumo/Summary, Contexto técnico/Technical Context, Conformidade/Constitution
     Check, Estrutura/Project Structure, Complexidade/Complexity Tracking) no formato da Parte B.
     Artefatos de apoio gerados pelo comando: research.md, data-model.md, contracts/, quickstart.md. -->
# Fxx — <Nome da feature> — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Branch:** `<branch>` · **Data:** <AAAA-MM-DD> · **Status da spec:** <status> · **ADRs:** <ADR-00x ou —>

## Parte B — Plano técnico (Gate 1)

### Resumo (Summary)
<!-- 2–4 linhas: o que a feature entrega (RFs principais) e a abordagem técnica escolhida. -->

### Contexto técnico (Technical Context)
<!-- Valores padrão do projeto (Constituição › Restrições de Stack). Altere só o que a feature muda;
     marque incertezas como NEEDS CLARIFICATION para o research.md resolver. -->
| Item | Valor |
|---|---|
| **Backend** | Python 3.12, FastAPI, Pydantic v2, uv |
| **Frontend** | React 19 + TypeScript strict, Vite, TanStack Query |
| **Agente** | Loop próprio + `google-genai`, Gemini no Vertex AI (só se a feature tocar `app/agent/`) |
| **Dados** | Firestore, sempre sob `users/{uid}/…` |
| **Integrações** | <Jira (httpx, API v3/ADF), LLM, … ou N/A> |
| **Testes** | pytest + respx + emuladores; Vitest + MSW; Playwright + axe (aceitação) |
| **Metas de desempenho** | <ex.: primeiro token p75 ≤ 3 s; p95 da rota ≤ 500 ms> |
| **Restrições** | <limites de volume, timeouts, cotas> |
| **Feature flag** | <nome e padrão, ou "não usa"> |

### Conformidade com a Constituição (Constitution Check)
*Gate: precisa passar antes do research.md e ser revisto depois do desenho.*

| Artigo | Verificação nesta feature | Status |
|---|---|---|
| I Spec antes do código | Spec com Gate 0; todo RF tem cenário AT | ⬜ |
| II Privacidade | Dados sob `users/{uid}`; `uid` do token; nada de estado global | ⬜ |
| III Segredos | Secret Manager / KMS; nada retorna ao cliente | ⬜ |
| IV Humano no controle | Escrita externa só via ação proposta + confirmação (ou N/A) | ⬜ |
| V Contrato primeiro | Rotas e esquemas definidos abaixo antes do código; cliente TS regenerado | ⬜ |
| VI Testes | Cobertura ≥ 80% back / 70% front; teste de aceitação automatizado | ⬜ |
| VII Simplicidade | Nenhum componente novo de infra sem ADR | ⬜ |
| VIII IaC | Recursos novos em Terraform; deploy reversível < 5 min | ⬜ |
| IX Observabilidade | Indicador da spec (§1) instrumentado | ⬜ |
| X UX e acessibilidade | pt-BR, WCAG 2.1 AA, erros com ação sugerida (ou N/A) | ⬜ |
| XI Qualidade do agente | Prompt versionado, ferramentas puras, evals (ou N/A) | ⬜ |
| XII Specs para agentes | Issues geradas pelo esquema `AgentReadySpec` com prontidão verificada (ou N/A) | ⬜ |

### 7. Desenho
- **Componentes afetados:** <camadas `api → services → agent | integrations | repositories → core`
  e/ou pastas do frontend>
- **Contrato de API:** <rotas `/api/v1/…`, request/response, códigos de erro (`code=…`), eventos SSE>.
  Detalhe em `contracts/`.
- **Dados (Firestore):** <coleções, campos, índices novos>. Detalhe em `data-model.md`.
- **Infra:** <recursos Terraform novos/alterados, ou "nenhum">
- **Decisões:** <decisões relevantes; estruturais viram ADR>. Detalhe em `research.md`.

### Estrutura (Project Structure)

```text
specs/0xx-slug/
├── spec.md          # Gate 0 + rastreabilidade/evidências
├── plan.md          # este arquivo (/speckit-plan)
├── research.md      # decisões e alternativas (/speckit-plan)
├── data-model.md    # entidades Firestore (/speckit-plan)
├── contracts/       # rotas, esquemas, eventos (/speckit-plan)
├── quickstart.md    # roteiro de validação (/speckit-plan)
└── tasks.md         # /speckit-tasks

backend/app/
├── api/v1/          # <routers novos/alterados>
├── services/        # <casos de uso>
├── agent/           # <grafo, ferramentas, prompts — se aplicável>
├── integrations/    # <clientes externos>
├── repositories/    # <acesso ao Firestore>
└── core/            # <config, segurança, logging, crypto>
backend/tests/{unit,integration,contract,acceptance}/

frontend/src/        # <rotas, features/, lib/>
frontend/e2e/        # <cenários Playwright AT-Fxx-nn>
infra/               # <Terraform, se houver>
```
<!-- Remova as linhas que a feature não toca e escreva os caminhos reais. -->

### 9. Plano de testes
| Camada | O que cobre |
|---|---|
| Unitário | <regras de domínio, validações, limites> |
| Integração | <serviço + emulador Firestore / Jira fake> |
| Contrato | <esquemas OpenAPI/SSE> |
| E2E / aceitação | AT-Fxx-01..nn |
| Evals | <se mudar prompt, modelo ou ferramentas; senão N/A> |

### Riscos e rollback
| Risco | Mitigação |
|---|---|
| <risco> | <mitigação> |

**Rollback:** <como desfazer: revisão anterior do Cloud Run, flag desligada, dados aditivos…>

### Complexidade justificada (Complexity Tracking)
> Preencha **só** se a Conformidade tiver exceção. Toda exceção exige ADR aprovado pelo dono do produto.

| Exceção (artigo) | Por que é necessária | Alternativa mais simples descartada porque |
|---|---|---|

### Gate 1 — Plano aprovado
- [ ] Contrato da API definido antes do código (front e back podem trabalhar em paralelo)
- [ ] Riscos e plano de rollback descritos
- [ ] Estimativa cabe na fase do roadmap; senão, a feature é dividida
- [ ] Conformidade com a Constituição sem exceção não justificada
