# F10 — Histórico de issues criados

| Campo | Valor |
|---|---|
| **Status** | Em validação |
| **Fase** | 2 — Produto |
| **Dependências** | F06, F08 |
| **Estimativa** | 3,5 dias |
| **Revisão** | 2026-11-16: issues escritas para agentes de IA de código ([doc 10](../../docs/modernizacao/10-specs-para-agentes.md), ADR-007) · 2026-11-17: contra o código da F06 em produção — o registro `users/{uid}/jira_issues/{key}` já é gravado ao criar; atualizações passam a ser registradas; filtros sem índices compostos (volume por usuário pequeno, sem mudar infra); status de várias issues numa só JQL; "Copiar para agente" a partir da spec guardada na ação; conversa excluída limpa o vínculo |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** a lista de issues criados vive só na sessão e se perde no refresh; links quebram (D10).
- **Objetivo:** histórico permanente de tudo que o usuário exportou ao Jira pelo app, com filtros e volta à conversa de origem.
- **Indicador:** issues exportados por usuário/semana (métrica de valor do produto).

### 2. Escopo
- **Inclui:** página "Created issues", filtros (projeto, tipo, período, prontidão), link para o Jira e para a conversa
  de origem, status atual sob demanda e "Copiar para agente de código". A tela já existe (F08, T008) com dados de
  demonstração; aqui ela passa a usar a API real.
- **Fora de escopo:** issues criados fora do app; sincronização contínua de status.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F10-RF-01 | O usuário vê os issues criados/atualizados pelo app, do mais recente ao mais antigo (pela 1ª vez que o app tocou na issue), com chave, tipo, título, projeto, data e se foi criada ou só atualizada | Must |
| F10-RF-02 | O histórico persiste entre sessões e dispositivos | Must |
| F10-RF-03 | O usuário filtra por projeto, tipo e período | Should |
| F10-RF-04 | Cada item tem link funcional para o Jira e para a conversa de origem | Must |
| F10-RF-05 | O usuário pode ver o status atual dos issues listados no Jira (consulta sob demanda); issue apagada no Jira aparece como "não encontrada" | Could |
| F10-RF-06 | Cada item tem "Copiar para agente de código": copia a chave, o link, o título, o Markdown da spec que o SpecFlow gravou (a última versão confirmada) e uma instrução curta de uso ("Implemente a issue ABC-12 abaixo; os critérios de aceite são os testes de pronto") (RA-30). Sem spec guardada (atualização só de título/labels), o botão explica que não há spec | Should |
| F10-RF-07 | A lista mostra se a issue foi gravada como pronta para agente (`agent-ready`), `human-only` ou não pronta (pelas labels confirmadas) e filtra por isso | Should |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F10-RT-01 | Registro gravado no mesmo commit (batch) que conclui a ação (F06), na criação e na atualização; a atualização não muda a data da 1ª gravação | unit + integração |
| F10-RT-02 | `GET /api/v1/jira/issues` ordena por `createdAt desc` com cursor; período como intervalo em `createdAt` na consulta; projeto, tipo e prontidão filtrados no servidor lendo em lotes (sem índices compostos — o volume por usuário é pequeno; leitura limitada a 1000 registros por página pedida). Índices compostos via Terraform só se o volume pedir | unit + integração |
| F10-RT-03 | Item cuja conversa foi excluída continua no histórico, sem link de conversa: a exclusão da conversa (F07) limpa o `conversationId` dos registros no mesmo processo | integração |
| F10-RT-04 | Migração: não há importação (o histórico do Streamlit era volátil); os registros gravados desde a F06 em produção já entram na lista | revisão |
| F10-RT-05 | Status: `POST /api/v1/jira/issues/status` com até 50 chaves numa única JQL (`key in (…)`); erros do Jira como na F09 (credencial recusada marca a conexão inválida) | unit |
| F10-RT-06 | "Copiar para agente": `GET /api/v1/jira/issues/{key}/agent-prompt` monta o texto da spec da ação mais recente com spec (`to_markdown`), sem chamar o Jira; 404 `spec-unavailable` se não houver | unit |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Histórico de issues

  Cenário: AT-F10-01 Issue confirmado aparece e persiste        # F10-RF-01, F10-RF-02, F10-RF-04
    Dado que confirmei a criação de "<KEY>-<n>" em uma conversa
    Quando abro "Created issues" em outra sessão logada na mesma conta
    Então vejo "<KEY>-<n>" no topo com tipo, título, projeto e data
    E o link do Jira aponta para "<site>/browse/<KEY>-<n>"
    E o link da origem abre a conversa

  Cenário: AT-F10-02 Filtros                                     # F10-RF-03
    Dado issues de tipos diferentes no histórico
    Quando filtro por projeto e tipo
    Então vejo apenas as issues daquele projeto e tipo

  Cenário: AT-F10-03 Status atual                                # F10-RF-05
    Quando clico em "Refresh Jira status"
    Então vejo o status atual de "<KEY>-<n>" no Jira (ex.: "To Do")

  Cenário: AT-F10-04 Copiar para agente de código               # F10-RF-06, F10-RF-07
    Dado que confirmei "<KEY>-<n>" como pronta para agente
    Quando abro "Created issues"
    Então vejo "<KEY>-<n>" marcada "Agent-ready"
    Quando clico em "Copy for coding agent"
    Então a área de transferência tem "<KEY>-<n>", a seção "## Critérios de aceite" e a instrução de uso
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| II Privacidade | `users/{uid}/jira_issues`; incluso na exportação/exclusão (F03) |
| XII Specs para agentes | Entrega da spec ao agente de código pelo "Copiar para agente" |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F10-RF-01 | AT-F10-01, `test_jira_issues.py`, `IssuesPage.test.tsx`, `http.test.ts` | ✅ |
| F10-RF-02 | AT-F10-01, `test_jira_issues.py` | ✅ |
| F10-RF-03 | AT-F10-02, `test_jira_issues.py`, `IssuesPage.test.tsx` | ✅ |
| F10-RF-04 | AT-F10-01, `test_jira_issues.py`, `IssuesPage.test.tsx` | ✅ |
| F10-RF-05 | AT-F10-03, `test_jira_issues.py`, `IssuesPage.test.tsx` | ✅ |
| F10-RF-06 | AT-F10-04, `test_jira_issues.py`, `IssuesPage.test.tsx` | ✅ |
| F10-RF-07 | AT-F10-04, `test_jira_issues.py`, `IssuesPage.test.tsx` | ✅ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
| 2026-11-17 | `feat/F10-historico-issues` | Local: Vite + API (Gemini `gemini-3.5-flash-lite` no Vertex, `pcb-inspect`) + emuladores, Jira sandbox `SCRUM` | `E2E_EMULATORS=1 E2E_REAL_LLM=1 E2E_JIRA_WRITE=1 npx playwright test e2e/f10-historico.spec.ts`, com autorização do PO para escrever | AT-F10-01..03 ok com SCRUM-40 (outra sessão vê no topo, link `/browse/SCRUM-40`, filtros projeto/tipo no servidor, status "A fazer"); AT-F10-04 (selo Agent-ready, cópia com instrução, link e `## Critérios de aceite`, origem abre a conversa) conferido na mesma conta sem nova escrita, depois de corrigir o aviso duplicado de "copied". SCRUM-39 criada numa 1ª execução que parou num erro do próprio teste. Issues mantidas no sandbox a pedido do PO | |
| 2026-11-17 | `feat/F10-historico-issues` | Unit + Firestore do emulador | `make test` (backend 553, front 136), `tests/integration/test_jira_issues.py` | registro e ação na mesma transação; atualização não muda a 1ª data; ordem, cursor e período na consulta real; conversa excluída limpa o vínculo | |
| 2026-11-18 | `d561fd8` (merge do PR #25) | prd (pcb-inspect) | `make deploy`: revisão `specflow-api-00014-mjt` com 100% do tráfego (rollback: `specflow-api-00013-vrs`), smoke `/health` na versão `d561fd8dc788` e smoke do modelo; `GET /api/v1/jira/issues`, `POST /api/v1/jira/issues/status` e `GET /api/v1/jira/issues/{key}/agent-prompt` sem token → 401; SPA publicado (bundle 220,6 kB gzip), `/issues` → 200 | ok, sem erros nos logs da revisão. Histórico com dados reais em produção ainda não exercitado | PO (aceite com as evidências locais) |
