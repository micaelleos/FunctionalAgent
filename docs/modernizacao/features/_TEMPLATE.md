# Fxx — <Nome da feature>

| Campo | Valor |
|---|---|
| **Status** | Rascunho · Spec aprovada · Planejada · Em implementação · Em validação · Aceita · Em produção |
| **Fase** | 0 / 1 / 2 / 3 / 4 |
| **Responsável** | <nome> |
| **Dependências** | Fxx, Fyy |
| **ADRs relacionados** | ADR-00x |
| **Estimativa** | <n> dias |

---

## Parte A — Especificação (Gate 0)

### 1. Contexto e objetivo
- **Problema:** o que dói hoje (referencie itens do diagnóstico `Dnn` quando houver).
- **Objetivo:** o que muda para o usuário/sistema.
- **Indicador de sucesso:** como saberemos em produção (Artigo IX).

### 2. Escopo
- **Inclui:** …
- **Fora de escopo:** …

### 3. Requisitos funcionais
| ID | Requisito | Prioridade |
|---|---|---|
| Fxx-RF-01 | O sistema deve … | Must |

### 4. Requisitos técnicos / não funcionais
| ID | Requisito | Como verificar |
|---|---|---|
| Fxx-RT-01 | … | teste / métrica / revisão |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: …

  Cenário: AT-Fxx-01 …   # cobre Fxx-RF-01
    Dado …
    Quando …
    Então …
```
Roteiro manual (somente o que não for automatizável): …

### 6. Conformidade com a Constituição
| Artigo | Como esta feature cumpre | Exceção? |
|---|---|---|
| II Privacidade | … | Não |
| III Segredos | … | Não |
| IV Humano no controle | … | Não |
| V Contrato | … | Não |
| VI Testes | … | Não |

---

## Parte B — Plano técnico (Gate 1)

### 7. Desenho
- **Componentes afetados:**
- **Contrato de API:** rotas, request/response, erros, eventos.
- **Dados (Firestore):** coleções/campos/índices novos.
- **Infra:** recursos Terraform novos/alterados.
- **Feature flag:** nome e padrão.
- **Rollback:** como desfazer.

### 8. Tarefas
| # | Tarefa | Teste que acompanha | Est. |
|---|---|---|---|
| 1 | … | … | 0,5 d |

### 9. Plano de testes
| Camada | O que cobre |
|---|---|
| Unitário | … |
| Integração | … |
| Contrato | … |
| E2E / aceitação | AT-Fxx-01..nn |
| Evals | … |

---

## Parte C — Validação (Gates 3 e 4)

### 10. Matriz de rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| Fxx-RF-01 | AT-Fxx-01, `path::test` | ⬜ |

### 11. Evidências
| Data | Versão/commit | Ambiente | Execução (link CI) | Resultado | Aceito por |
|---|---|---|---|---|---|
| | | dev | | | |
