# F14 — Editor de artefatos antes da exportação

| Campo | Valor |
|---|---|
| **Status** | Rascunho (Fase 4 — detalhar plano técnico após GA) |
| **Fase** | 4 — Evolução |
| **Dependências** | F06, F08 |
| **Estimativa** | 7 dias |

> [Spec](spec.md) · [Plano](plan.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** para mudar uma vírgula numa story proposta, o usuário precisa pedir ao agente e esperar nova proposta.
- **Objetivo:** editar título, descrição (Markdown com prévia), prioridade, tipo e pai diretamente no cartão antes de
  confirmar; pedir ao agente refinamentos de um trecho específico.
- **Indicador:** % de propostas editadas antes de confirmar; queda no número de turnos por issue criado.

### 2. Escopo
- **Inclui:** modo edição do `ActionCard`, nova versão do payload (novo hash, histórico de versões), "Refinar com IA"
  aplicado a um campo, rascunhos salvos (`users/{uid}/artifacts`).
- **Fora de escopo:** edição colaborativa em tempo real.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F14-RF-01 | O usuário edita os campos de uma proposta pendente e vê a prévia atualizada | Must |
| F14-RF-02 | Ao confirmar, é criado exatamente o conteúdo editado | Must |
| F14-RF-03 | O usuário pode desfazer edições e voltar à versão do agente | Should |
| F14-RF-04 | O usuário seleciona um campo e pede "Refinar com IA" com uma instrução | Should |
| F14-RF-05 | O agente passa a considerar a versão editada nos turnos seguintes | Must |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F14-RT-01 | Edição gera nova versão imutável com novo `payloadHash`; confirmação referencia a versão | unit |
| F14-RT-02 | Validação do payload igual à da ferramenta do agente (mesmo esquema Pydantic) | contrato |
| F14-RT-03 | Autosave de rascunho a cada 2 s de inatividade | Vitest |

### 5. Teste final de aceitação
```gherkin
  Cenário: AT-F14-01 Editar e confirmar                         # F14-RF-01, F14-RF-02
    Dado uma proposta de story pendente
    Quando altero o título para "Login com SSO" e adiciono um critério de aceite
    E confirmo
    Então o issue no Jira tem o título "Login com SSO" e o novo critério

  Cenário: AT-F14-02 Refinar trecho com IA                       # F14-RF-04, F14-RF-05
    Quando seleciono a descrição e peço "adicione cenário de senha expirada"
    Então a descrição proposta passa a ter o cenário "Senha expirada"
    E ao perguntar "qual o título atual?" o agente responde "Login com SSO"
```

### 6. Conformidade com a Constituição
IV (o que se confirma é exatamente o que se vê — inclusive após edição), XI.
