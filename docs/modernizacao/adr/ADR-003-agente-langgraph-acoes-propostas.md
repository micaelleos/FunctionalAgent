# ADR-003 — Agente com LangGraph, sem estado no processo, e padrão "ação proposta"

- **Status:** Proposto · **Data:** 2026-11-13

## Contexto

O agente atual usa `AgentExecutor` + `ConversationBufferMemory` (APIs descontinuadas do LangChain), com memória
global ao processo (vazamento entre usuários, D01) e escrita no Jira condicionada apenas ao prompt (D04).
Precisamos de: streaming real, isolamento por usuário, testabilidade e garantia de confirmação humana.

## Opções consideradas

1. Atualizar para LangChain moderno mantendo `AgentExecutor` — descontinuado, não resolve confirmação.
2. **LangGraph** (`create_react_agent` ou grafo próprio) — padrão atual do ecossistema LangChain, streaming de
   tokens/eventos, controle de iterações.
3. Loop próprio sobre a API do provedor (tool calling manual) — máximo controle, mais código para manter.
4. LangGraph `interrupt()` + checkpointer persistente para confirmação humana.

## Decisão

- **LangGraph** para o loop do agente (opção 2), com o modelo instanciado por configuração (`init_chat_model`),
  permitindo trocar de provedor sem mudar o grafo.
- **Sem estado no processo:** a cada turno o histórico é carregado do Firestore; nada de memória global.
- **Confirmação humana via "ação proposta"** (em vez de `interrupt()` + checkpointer):
  - Ferramentas de escrita (`propor_criacao_issue`, `propor_atualizacao_issue`) **não chamam o Jira**; validam o
    payload, gravam `pending_actions/{id}` e devolvem ao LLM "ação proposta, aguardando confirmação".
  - O endpoint `POST /actions/{id}/confirm` executa a chamada ao Jira de forma determinística, sem o LLM.

## Motivos para "ação proposta" em vez de `interrupt()`

- Não exige checkpointer persistente no Firestore (não há implementação oficial; seria código a manter).
- O payload executado é **exatamente** o que o usuário viu (hash conferido), atendendo ao Artigo IV.
- A execução é idempotente via transação de estado; fácil de testar sem LLM.
- O usuário pode confirmar horas depois, até em outra aba; o agente é informado no turno seguinte.

## Consequências

- ✅ Elimina D01 e D04 por construção; ferramentas testáveis isoladamente.
- ✅ Streaming real de tokens e eventos de ferramenta.
- ⚠️ Reconstruir o histórico a cada turno custa leituras e tokens → janela de mensagens + sumarização
  (`conversation.summary`) quando passar do orçamento.
- ⚠️ Comportamento do agente pode mudar na migração → baseline de evals com o prompt atual **antes** de migrar (F05/F15).
