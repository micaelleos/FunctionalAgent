# F07 — Conversas persistentes

| Campo | Valor |
|---|---|
| **Status** | Em validação |
| **Revisão** | 2026-11-17: alinhada à F05/F06 já em produção — ações reidratadas pela rota da F06, título pelo mesmo modelo em paralelo ao turno, exclusão sem apagar o que já está no Jira, aceitação pela API (a tela é da F08) |
| **Fase** | 2 — Produto |
| **Dependências** | F05, F06 |
| **ADRs** | ADR-001 |
| **Estimativa** | 5 dias |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** a conversa some no refresh; não há como manter vários assuntos separados.
- **Objetivo:** várias conversas por usuário, listadas, retomáveis, renomeáveis e excluíveis.
- **Indicador:** % de usuários que retomam uma conversa antiga (≥ 1 por semana).

### 2. Escopo
- **Inclui:** API de conversas (CRUD + histórico paginado), título automático, associação opcional a um projeto Jira
  (`projectKey` como contexto padrão do agente), reidratação de cartões de ação (com a ação embutida na mensagem).
- **Fora de escopo:** busca textual no histórico, compartilhar conversa, pastas, a tela (sidebar e histórico são da
  F08), apagar issues do Jira ao excluir a conversa.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F07-RF-01 | O usuário cria uma nova conversa | Must |
| F07-RF-02 | O usuário vê suas conversas ordenadas pela última atividade, com título e data | Must |
| F07-RF-03 | Ao abrir uma conversa, vê todo o histórico (incluindo cartões de ação e seus estados); só mensagens do usuário e do agente, sem as notas internas para o modelo | Must |
| F07-RF-04 | O título é gerado automaticamente a partir da 1ª mensagem e pode ser renomeado; um título renomeado nunca é sobrescrito | Should |
| F07-RF-05 | O usuário pode excluir uma conversa (com confirmação), apagando mensagens e ações; as issues já criadas continuam no Jira e no histórico de issues (F10) | Must |
| F07-RF-06 | O usuário pode fixar (ou soltar) um projeto Jira na conversa, usado como padrão pelo agente sem perguntar | Should |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F07-RT-01 | Listagem e histórico paginados por cursor (`limit` ≤ 50) | contrato |
| F07-RT-02 | Listagem por `updatedAt desc` (índice de campo único, automático; sem índice composto); p95 < 300 ms com 500 conversas | teste de desempenho no emulador |
| F07-RT-03 | Exclusão recursiva idempotente (conversa, mensagens e ações da conversa); ação em execução no Jira impede a exclusão (409) | integração |
| F07-RT-04 | `updatedAt` e `messageCount` atualizados na mesma transação/batch da mensagem | integração |
| F07-RT-05 | Título automático pelo mesmo modelo do agente (`gemini-3.5-flash-lite`, já o mais barato), em paralelo ao 1º turno e gravado antes do `done`, sem atrasar os tokens; falha mantém o título provisório (1ª mensagem truncada) | unit + integração |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Conversas persistentes

  # Pela API local com o Gemini e o Jira sandbox (a tela é da F08, que repete estes cenários no navegador).

  Cenário: AT-F07-01 Retomar conversa                              # F07-RF-01, F07-RF-03
    Dado que criei uma conversa e troquei 3 mensagens com o agente
    Quando abro o histórico da conversa
    Então vejo as 3 mensagens e as 3 respostas na ordem original, sem notas internas

  Cenário: AT-F07-02 Lista ordenada e título automático            # F07-RF-02, F07-RF-04
    Dado uma conversa sobre login e depois uma nova sobre checkout
    Então a lista mostra primeiro a de checkout, com título gerado contendo "checkout"
    Quando renomeio para "Checkout v2" e mando outra mensagem
    Então a lista mostra "Checkout v2" no topo

  Cenário: AT-F07-03 Cartões de ação persistem                     # F07-RF-03
    Dado uma conversa com uma ação confirmada e outra pendente
    Quando abro o histórico da conversa
    Então a mensagem do agente traz uma ação "done" com chave e link e outra "pending"

  Cenário: AT-F07-04 Excluir conversa                              # F07-RF-05
    Quando excluo a conversa "Checkout v2"
    Então ela some da lista, GET da conversa retorna 404 e a ação pendente dela retorna 404
    E a issue criada nela continua no Jira

  Cenário: AT-F07-05 Projeto padrão                                 # F07-RF-06
    Dado uma conversa com o projeto fixado SCRUM
    Quando peço "crie uma task de revisão de copy da tela de checkout" sem dizer o projeto
    Então a proposta é para o projeto SCRUM, sem o agente perguntar o projeto
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| II Privacidade | Tudo sob `users/{uid}`; conversa de outro usuário → 404; exclusão real (mensagens e ações apagadas) |
| IV Humano no controle | Excluir a conversa não escreve no Jira; ação em execução bloqueia a exclusão |
| V Contrato | Paginação por cursor opaco, `limit` ≤ 50, igual em listagem e histórico; tipos do front gerados do OpenAPI |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F07-RF-01 | AT-F07-01, `test_conversations.py`, `test_conversations_api.py` | ✅ unit · ✅ aceitação |
| F07-RF-02 | AT-F07-02, `test_conversations.py`, `integration/test_conversations.py` | ✅ unit · ✅ aceitação |
| F07-RF-03 | AT-F07-01, AT-F07-03, `test_conversations.py` | ✅ unit · ✅ aceitação |
| F07-RF-04 | AT-F07-02, `test_conversation_title.py` | ✅ unit · ✅ aceitação |
| F07-RF-05 | AT-F07-04, `test_conversations.py`, `integration/test_conversations.py` | ✅ unit · ✅ aceitação |
| F07-RF-06 | AT-F07-05, `test_chat_service.py`, eval `pinned_project_*` | ✅ unit · ✅ aceitação |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
| 2026-11-17 | PR #19 (`feat/F07-conversas-persistentes`) | Local: API + emuladores, Gemini `gemini-3.5-flash-lite` (Vertex, `pcb-inspect`), Jira sandbox `SCRUM` | `pytest tests/acceptance` AT-F07-01..05 em 2 execuções (a 2ª junto com AT-F05); evals 33 casos | 5/5 e 14/14; issues mantidas a pedido do PO (SCRUM-30..33); evals sem métrica abaixo do baseline, `pinned_project` 100% (`evals/results/2026-11-17-new-gemini-3.5-flash-lite-f07.json`); integração: p95 da listagem com 500 conversas < 300 ms | Pendente (PO) |
