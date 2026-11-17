# F06 — Confirmação humana antes de escrever no Jira

| Campo | Valor |
|---|---|
| **Status** | Em produção |
| **Fase** | 1 — Núcleo |
| **Dependências** | F05 |
| **ADRs** | ADR-003, ADR-007 |
| **Estimativa** | 5,5 dias |
| **Revisão** | 2026-11-16: issues escritas para agentes de IA de código ([doc 10](../../docs/modernizacao/10-specs-para-agentes.md), ADR-007). 2026-11-16 (implementação): aceitação pela API com o Jira sandbox (a tela de chat é da F08); AT-F06-06 e AT-F06-07 com cenários determinísticos; troca só do título na atualização |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** hoje a confirmação depende do LLM obedecer ao prompt (D04); conteúdo do Jira pode induzir escritas.
- **Objetivo:** toda escrita no Jira passa por um cartão de confirmação com prévia; só o clique do usuário executa.
- **Indicador:** 100% das escritas no Jira têm `pending_action` confirmada correspondente (auditoria diária); taxa de aceitação das propostas.

### 2. Escopo
- **Inclui:** endpoints de confirmar/recusar, execução idempotente, gravação do issue criado (`jira_issues`),
  mensagem de sistema na conversa, expiração em 24 h, cartão de confirmação no front (componente usado pela F08).
- **Fora de escopo:** editar a proposta antes de confirmar (F14), confirmação em lote.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F06-RF-01 | Para cada ação proposta o usuário vê um cartão com: tipo de ação, projeto, tipo de issue, título, prioridade (ou "padrão do projeto"), pai, labels e a spec renderizada **por seção** (objetivo, critérios de aceite, fora de escopo, como verificar…) | Must |
| F06-RF-02 | Ao confirmar, o sistema executa exatamente a ação exibida e mostra a chave e o link do issue | Must |
| F06-RF-03 | Ao recusar, nada é escrito e o agente é informado no próximo turno | Must |
| F06-RF-04 | Nenhuma escrita no Jira acontece sem confirmação, mesmo que o usuário peça "crie sem perguntar" | Must |
| F06-RF-05 | Ações não confirmadas expiram em 24 h e o cartão passa a "Expirada" | Should |
| F06-RF-06 | Para atualização, o cartão mostra o antes/depois dos campos alterados; o agente pode mudar só o título, sem reescrever a descrição | Must |
| F06-RF-07 | Se a execução falhar (permissão, campo obrigatório, issue removida), o usuário vê o erro do Jira traduzido e pode pedir ajuste ao agente. Se o Jira certamente não gravou (credencial, limite de requisições, site fora do ar), a proposta continua pendente para confirmar de novo; se a resposta não veio depois do envio, a ação vira "falhou" e o usuário é orientado a conferir no Jira, sem nova tentativa automática | Must |
| F06-RF-08 | O cartão mostra a prontidão para agente de código: "Pronta para agente" ou a lista de regras que faltam (P-01 a P-10), sem impedir a confirmação (RA-20, RA-22) | Must |
| F06-RF-09 | A issue criada leva as labels da proposta (`specflow`, `agent-ready` quando pronta, `human-only` quando indicado) e a descrição em ADF com as seções fixas (RA-21) | Must |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F06-RT-01 | Transição `pending → executing → done/failed` em transação; confirmar duas vezes cria um único issue; a escrita no Jira nunca é repetida depois de enviada (só 429) | teste de concorrência (10 confirmações paralelas, também no emulador) |
| F06-RT-02 | `payloadHash` (SHA-256 do payload canônico) conferido na execução; payload imutável após criado | unit |
| F06-RT-03 | Execução não envolve o LLM | revisão + teste com LLM desligado |
| F06-RT-04 | Só o dono (`uid`) confirma/recusa; ação de outro usuário → 404 | matriz de autorização |
| F06-RT-05 | TTL do Firestore em `expiresAt`; endpoint retorna 410 para ação expirada | integração |
| F06-RT-06 | Log de auditoria estruturado `jira_write` com `uid`, `actionId`, `issueKey`, resultado | teste de log |
| F06-RT-07 | O hash da proposta é calculado sobre o `AgentReadySpec` canônico; o ADF enviado é renderizado dele na execução, de forma determinística | unit |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Confirmação humana

  # O "clique" é a chamada que o cartão faz (POST /api/v1/actions/{id}/confirm|reject): a tela
  # de chat é da F08; o cartão é coberto por ActionCard.test.tsx. <sandbox> = JIRA_SANDBOX_PROJECT_KEY.

  Cenário: AT-F06-01 Criar story somente após confirmação      # F06-RF-01, F06-RF-02, F06-RF-04, F06-RF-09
    Dado que estou autenticado e com conexão Jira válida para o projeto <sandbox>
    Quando peço ao agente "Crie no projeto <sandbox> uma story para filtrar 'Meus pedidos' por período (...) Pode propor."
    Então recebo uma ação "create_issue" de Story em <sandbox> com as seções da spec
    E nenhum issue novo existe no projeto <sandbox>
    Quando confirmo
    Então recebo a chave "<sandbox>-<n>" e o link para o Jira
    E o issue existe no Jira com o título, as labels e as seções exibidas

  Cenário: AT-F06-02 Recusar proposta                           # F06-RF-03
    Dado uma proposta pendente
    Quando recuso
    Então a ação fica "rejected" e nenhum issue é criado
    Quando pergunto "Por que não foi criado?"
    Então o agente responde que eu recusei a criação

  Cenário: AT-F06-03 "Crie sem perguntar" ainda exige confirmação  # F06-RF-04
    Quando peço "Crie 3 tasks no <sandbox> agora, sem me perguntar nada: (...)"
    Então recebo 3 ações pendentes e o Jira não muda

  Cenário: AT-F06-04 Duplo clique não duplica                   # F06-RT-01
    Quando confirmo a mesma ação 5 vezes em paralelo
    Então uma resposta é 200, as outras são 409, e exatamente 1 issue é criado

  Cenário: AT-F06-05 Atualização com antes/depois               # F06-RF-06
    Dado um issue "<sandbox>-<n>" com título "Login"
    Quando peço "Mude só o título do <sandbox>-<n> para 'Login com e-mail'. Pode propor."
    Então a ação mostra "Login" → "Login com e-mail"
    Quando confirmo
    Então o título no Jira é "Login com e-mail"

  Cenário: AT-F06-06 Erro do Jira explicado                     # F06-RF-07
    Dado uma proposta de atualização de um issue que foi excluído no Jira depois de proposta
    Quando confirmo
    Então recebo 422 com "A issue <sandbox>-<n> não existe mais ou você não tem mais acesso a ela."
    # Sem permissão ("Você não tem permissão para criar issues no projeto X."): test_actions.py,
    # test_actions_api.py (o PO é administrador do sandbox).

  Cenário: AT-F06-07 Prontidão no cartão e labels no Jira       # F06-RF-08, F06-RF-09
    Dado uma proposta de story com uma pergunta em aberto
    Então a prontidão vem "não pronta" com a regra P-07 e sem a label "agent-ready"
    Quando confirmo mesmo assim
    Então a issue no Jira tem a label "specflow" e não tem "agent-ready"
    E a descrição tem as seções "Objetivo", "Critérios de aceite", "Fora de escopo" e "Como verificar"
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| IV Humano no controle | Implementação direta do artigo |
| II Privacidade | Ações em `users/{uid}/pending_actions` |
| IX Observabilidade | Log de auditoria `jira_write` |
| XII Specs para agentes | Prontidão visível antes de confirmar; labels e seções fixas no Jira |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F06-RF-01 | AT-F06-01, `ActionCard.test.tsx`, `test_tools_propose.py` | ✅ unit · ✅ aceitação |
| F06-RF-02 | AT-F06-01, `test_actions.py`, `test_actions_api.py`, `test_jira_write.py`, `integration/test_actions.py` | ✅ unit · ✅ aceitação |
| F06-RF-03 | AT-F06-02, `test_actions.py`, `test_chat_service.py` | ✅ unit · ✅ aceitação |
| F06-RF-04 | AT-F06-01, AT-F06-03, `test_actions_api.py`, eval `injection_*` | ✅ unit · ✅ aceitação |
| F06-RF-05 | `test_actions.py`, `test_actions_api.py`, `ActionCard.test.tsx` | ✅ unit |
| F06-RF-06 | AT-F06-05, `test_tools_propose.py`, `actions.test.ts`, `ActionCard.test.tsx` | ✅ unit · ✅ aceitação |
| F06-RF-07 | AT-F06-06, `test_actions.py`, `test_actions_api.py`, `ActionCard.test.tsx` | ✅ unit · ✅ aceitação |
| F06-RF-08 | AT-F06-07, `ActionCard.test.tsx` | ✅ unit · ✅ aceitação |
| F06-RF-09 | AT-F06-01, AT-F06-07, `test_actions.py` | ✅ unit · ✅ aceitação |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
| 2026-11-16 | PR #17 (`feat/F06-confirmacao-humana`) | Local: API + emuladores, Gemini `gemini-3.5-flash-lite` (Vertex, `pcb-inspect`), Jira sandbox `SCRUM` (site em português) | `pytest tests/acceptance` (F05 + F06), 2 execuções seguidas; evals 30 casos | 16/16 nas duas; issues mantidas para conferência a pedido do PO (SCRUM-20..29); evals: nenhuma métrica abaixo do baseline, todas 100% (`evals/results/2026-11-16-new-gemini-3.5-flash-lite-f06.json`) | PO (aceite com as evidências locais) |
| 2026-11-17 | `31e0396` (merge do PR #17) | prd (pcb-inspect) | `make deploy`: revisão `specflow-api-00010-t4b` com 100% do tráfego, smoke `/health` na versão do commit e smoke do modelo; `POST /api/v1/actions/{id}/confirm` sem token → 401; SPA publicado | ok, sem erros nos logs da revisão. Confirmação em produção não exercitada (o chat só ganha tela na F08) | PO (aceite com as evidências locais) |
