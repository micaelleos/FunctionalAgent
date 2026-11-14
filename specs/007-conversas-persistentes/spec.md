# F07 — Conversas persistentes

| Campo | Valor |
|---|---|
| **Status** | Rascunho |
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
  (`projectKey` como contexto padrão do agente), reidratação de cartões de ação.
- **Fora de escopo:** busca textual no histórico, compartilhar conversa, pastas.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F07-RF-01 | O usuário cria uma nova conversa | Must |
| F07-RF-02 | O usuário vê suas conversas ordenadas pela última atividade, com título e data | Must |
| F07-RF-03 | Ao abrir uma conversa, vê todo o histórico (incluindo cartões de ação e seus estados) | Must |
| F07-RF-04 | O título é gerado automaticamente após a 1ª troca e pode ser renomeado | Should |
| F07-RF-05 | O usuário pode excluir uma conversa (com confirmação), apagando mensagens e ações pendentes | Must |
| F07-RF-06 | O usuário pode fixar um projeto Jira na conversa, usado como padrão pelo agente | Should |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F07-RT-01 | Listagem e histórico paginados por cursor (`limit` ≤ 50) | contrato |
| F07-RT-02 | Índice `conversations(updatedAt desc)`; listagem p95 < 300 ms com 500 conversas | teste de desempenho no emulador/dev |
| F07-RT-03 | Exclusão recursiva idempotente | integração |
| F07-RT-04 | `updatedAt` e `messageCount` atualizados na mesma transação/batch da mensagem | integração |
| F07-RT-05 | Título automático via chamada barata ao LLM (modelo pequeno), assíncrona, sem bloquear o stream | integração |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Conversas persistentes

  Cenário: AT-F07-01 Retomar conversa após recarregar          # F07-RF-01, F07-RF-03
    Dado que criei uma conversa e troquei 3 mensagens com o agente
    Quando recarrego a página e abro a conversa
    Então vejo as 3 mensagens e respostas na ordem original

  Cenário: AT-F07-02 Lista ordenada e título automático         # F07-RF-02, F07-RF-04
    Dado as conversas "Login" (ontem) e uma nova sobre "checkout" (agora)
    Então a lista mostra primeiro a de checkout com título gerado contendo "checkout"
    Quando renomeio para "Checkout v2"
    Então a lista mostra "Checkout v2"

  Cenário: AT-F07-03 Cartões de ação persistem                  # F07-RF-03
    Dado uma conversa com uma ação confirmada e outra pendente
    Quando reabro a conversa
    Então vejo um cartão "Concluída" com link e um cartão "Pendente" com botões ativos

  Cenário: AT-F07-04 Excluir conversa                           # F07-RF-05
    Quando excluo a conversa "Checkout v2" e confirmo
    Então ela some da lista e GET da conversa retorna 404

  Cenário: AT-F07-05 Projeto padrão                              # F07-RF-06
    Dado a conversa com projeto fixado "E2E"
    Quando peço "crie uma task de revisão de copy"
    Então a proposta é para o projeto "E2E" sem o agente perguntar o projeto
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| II Privacidade | Tudo sob `users/{uid}`; exclusão real |
| V Contrato | Paginação padronizada |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F07-RF-01 | AT-F07-01 | ⬜ |
| F07-RF-02 | AT-F07-02 | ⬜ |
| F07-RF-03 | AT-F07-01, AT-F07-03 | ⬜ |
| F07-RF-04 | AT-F07-02 | ⬜ |
| F07-RF-05 | AT-F07-04 | ⬜ |
| F07-RF-06 | AT-F07-05 | ⬜ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
