<!-- Template de spec do projeto (substitui o spec-template do Spec Kit).
     Numere a feature como Fxx = número da pasta specs/0xx-slug. O plano técnico (Gate 1)
     vai em plan.md (/speckit-plan) e as tarefas em tasks.md (/speckit-tasks). -->
# Fxx — <Nome da feature>

| Campo | Valor |
|---|---|
| **Status** | Rascunho · Spec aprovada · Planejada · Em implementação · Em validação · Aceita · Em produção |
| **Fase** | 0 / 1 / 2 / 3 / 4 |
| **Responsável** | <nome> |
| **Dependências** | Fxx, Fyy |
| **ADRs relacionados** | ADR-00x |
| **Estimativa** | <n> dias |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

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

## Parte C — Validação (Gates 3 e 4)

### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| Fxx-RF-01 | AT-Fxx-01, `path::test` | ⬜ |

### 11. Evidências
| Data | Versão/commit | Ambiente | Execução (link CI) | Resultado | Aceito por |
|---|---|---|---|---|---|
| | | dev | | | |
