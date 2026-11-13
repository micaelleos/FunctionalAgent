# F10 — Histórico de issues criados

| Campo | Valor |
|---|---|
| **Status** | Rascunho |
| **Fase** | 2 — Produto |
| **Dependências** | F06, F08 |
| **Estimativa** | 3 dias |

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** a lista de issues criados vive só na sessão e se perde no refresh; links quebram (D10).
- **Objetivo:** histórico permanente de tudo que o usuário exportou ao Jira pelo app, com filtros e volta à conversa de origem.
- **Indicador:** issues exportados por usuário/semana (métrica de valor do produto).

### 2. Escopo
- **Inclui:** página "Issues criados", filtros (projeto, tipo, período), link para o Jira e para a conversa de origem,
  status atual do issue sob demanda.
- **Fora de escopo:** issues criados fora do app; sincronização contínua de status.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F10-RF-01 | O usuário vê os issues criados/atualizados pelo app, do mais recente ao mais antigo, com chave, tipo, título, projeto e data | Must |
| F10-RF-02 | O histórico persiste entre sessões e dispositivos | Must |
| F10-RF-03 | O usuário filtra por projeto, tipo e período | Should |
| F10-RF-04 | Cada item tem link funcional para o Jira e para a conversa de origem | Must |
| F10-RF-05 | O usuário pode ver o status atual do issue no Jira (consulta sob demanda) | Could |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F10-RT-01 | Registro gravado na mesma transação que conclui a ação (F06) | integração |
| F10-RT-02 | Índices `jira_issues(projectKey, createdAt desc)` e `(type, createdAt desc)`; paginação por cursor | contrato |
| F10-RT-03 | Item cuja conversa foi excluída continua no histórico, sem link de conversa | integração |
| F10-RT-04 | Migração: oferecer importação manual não é necessária (histórico antigo era volátil) — documentado | revisão |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Histórico de issues

  Cenário: AT-F10-01 Issue confirmado aparece e persiste        # F10-RF-01, F10-RF-02, F10-RF-04
    Dado que confirmei a criação de "E2E-<n>" em uma conversa
    Quando abro "Issues criados" em outro navegador logado na mesma conta
    Então vejo "E2E-<n>" no topo com tipo, título, projeto e data
    E o link do Jira abre "<site>/browse/E2E-<n>"
    E o link "Ver conversa" abre a conversa de origem

  Cenário: AT-F10-02 Filtros                                     # F10-RF-03
    Dado issues criados nos projetos "E2E" e "DEMO"
    Quando filtro por projeto "DEMO" e tipo "Epic"
    Então vejo apenas épicos de "DEMO"

  Cenário: AT-F10-03 Status atual                                # F10-RF-05
    Quando clico em "Ver status" em "E2E-<n>"
    Então vejo o status atual do Jira (ex.: "To Do")
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| II Privacidade | `users/{uid}/jira_issues`; incluso na exportação/exclusão (F03) |

## Parte B — Plano técnico
### 7. Desenho
`GET /api/v1/jira/issues?projectKey=&type=&from=&to=&cursor=`; `GET /api/v1/jira/issues/{key}/status`. Página `/issues` com tabela responsiva.
### 8. Tarefas
| # | Tarefa | Teste | Est. |
|---|---|---|---|
| 1 | Endpoint + índices + filtros | integração/contrato | 1 d |
| 2 | Página + filtros + status sob demanda | Vitest | 1 d |
| 3 | AT-F10-01..03 | Playwright | 1 d |
### 9. Plano de testes
Integração com emulador; E2E com sandbox.

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F10-RF-01 | AT-F10-01 | ⬜ |
| F10-RF-02 | AT-F10-01 | ⬜ |
| F10-RF-03 | AT-F10-02 | ⬜ |
| F10-RF-04 | AT-F10-01 | ⬜ |
| F10-RF-05 | AT-F10-03 | ⬜ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
