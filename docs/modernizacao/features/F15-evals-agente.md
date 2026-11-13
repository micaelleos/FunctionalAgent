# F15 — Suíte contínua de avaliação do agente (evals)

| Campo | Valor |
|---|---|
| **Status** | Rascunho (baseline mínimo entra na F05; suíte completa após GA) |
| **Fase** | 4 — Evolução (baseline na Fase 1) |
| **Dependências** | F05 |
| **Estimativa** | 5 dias |

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** mudanças de prompt, modelo ou ferramentas alteram o comportamento do agente de forma silenciosa.
- **Objetivo:** medir a qualidade do agente de forma reprodutível e impedir regressões (Artigos VI e XI).
- **Indicador:** score agregado das evals por versão, publicado em cada release.

### 2. Escopo
- **Inclui:** dataset dourado versionado (≥ 60 casos), métricas determinísticas + LLM-como-juiz com rubrica,
  execução em PR (subconjunto) e diária (completa), relatório comparativo por versão, limites de regressão.
- **Fora de escopo:** avaliação online com usuários (A/B) — backlog.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F15-RF-01 | Um comando roda as evals contra qualquer combinação prompt/modelo e gera relatório (Markdown + JSON) | Must |
| F15-RF-02 | O PR que altera o agente recebe comentário com o comparativo vs `master` | Must |
| F15-RF-03 | O release é bloqueado se alguma métrica cair além do limite | Must |

### 4. Métricas
| Métrica | Tipo | Limite de regressão |
|---|---|---|
| Ferramenta correta escolhida | determinística | −2 p.p. |
| Nunca escreve sem proposta | determinística | 100% obrigatório |
| Pede projeto quando ausente | determinística | −2 p.p. |
| Story em BDD válido (Cenário/Dado/Quando/Então + critérios) | regex/estrutura | −3 p.p. |
| Épico completo (objetivo, benefício, escopo, critérios) | estrutura | −3 p.p. |
| Resistência a prompt injection | determinística | 100% obrigatório |
| Qualidade textual (clareza, completude) | LLM-juiz 1–5 | −0,2 |
| Custo médio por caso | medido | +20% gera alerta |

### 5. Teste final de aceitação
```gherkin
  Cenário: AT-F15-01 Regressão bloqueia                          # F15-RF-02, F15-RF-03
    Dado um PR que remove do prompt a regra de escrever stories em BDD
    Quando o CI roda as evals
    Então o comentário mostra queda em "Story em BDD válido"
    E o check "evals" falha

  Cenário: AT-F15-02 Relatório local                              # F15-RF-01
    Quando executo "make evals PROMPT=v1 MODEL=<modelo>"
    Então é gerado "evals/reports/<data>-v1-<modelo>.md" com todas as métricas
```

### 6. Conformidade com a Constituição
VI (testes como portão), XI (qualidade do agente).

## Parte B — Plano técnico
Dataset em `backend/tests/evals/dataset/*.yaml` (entrada, contexto Jira simulado, expectativas). Execução com Jira
fake determinístico e LLM real. A detalhar no Gate 1.
