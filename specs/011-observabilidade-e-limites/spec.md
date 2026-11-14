# F11 — Observabilidade, limites de uso e proteção

| Campo | Valor |
|---|---|
| **Status** | Rascunho |
| **Fase** | 3 — Produção |
| **Dependências** | F05–F10 |
| **Estimativa** | 5 dias |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** sem logs estruturados, métricas, alertas nem controle de custo de LLM (D03, D17).
- **Objetivo:** operar com visibilidade (SLOs, alertas, dashboard), custo previsível (cotas) e proteção contra abuso (App Check).
- **Indicador:** SLOs medidos: disponibilidade 99,5%, p95 de turno < 30 s, primeiro token p75 < 3 s.

### 2. Escopo
- **Inclui:** logging estruturado com correlação, traces OpenTelemetry, métricas de negócio (log-based metrics),
  dashboard, alertas, SLOs, cotas diárias por usuário, App Check, rate limit por usuário, teste de carga, runbooks.
- **Fora de escopo:** painel administrativo de usuários; billing para usuários.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F11-RF-01 | O usuário vê seu consumo do dia (mensagens) e o limite | Should |
| F11-RF-02 | Ao atingir a cota diária, o usuário recebe mensagem clara com o horário de renovação | Must |
| F11-RF-03 | Requisições em excesso (rate limit) recebem "Muitas requisições, aguarde alguns segundos" | Must |
| F11-RF-04 | O responsável recebe alerta (e-mail) em erro elevado, latência alta, falha de LLM/Jira e orçamento | Must |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F11-RT-01 | Logs JSON com `severity`, `trace`, `request_id`, `uid_hash`; sem conteúdo de mensagens nem segredos | teste de log |
| F11-RT-02 | Traces: request → LLM → Jira → Firestore no Cloud Trace | verificação em dev |
| F11-RT-03 | Métricas: turnos, tokens, custo estimado, ações propostas/confirmadas, erros Jira por código, latência 1º token | dashboard |
| F11-RT-04 | Alertas: 5xx > 2% (5 min), p95 turno > 30 s, erro LLM > 5%, uptime check falhando, orçamento 90% | Terraform `monitoring` |
| F11-RT-05 | Cota diária configurável (`DAILY_MESSAGE_QUOTA`, `DAILY_TOKEN_QUOTA`) contada em `users/{uid}/usage/{dia}` com incremento atômico | integração |
| F11-RT-06 | Rate limit por `uid`: 10 mensagens/min (token bucket por instância + cota global no Firestore) | unit |
| F11-RT-07 | App Check obrigatório em prd (header `X-Firebase-AppCheck` verificado); modo "monitorar" em dev por 1 semana antes | integração |
| F11-RT-08 | Teste de carga: 50 usuários simultâneos com LLM fake, erro < 1%, p95 do overhead do backend < 500 ms | k6 |
| F11-RT-09 | Runbooks: rollback, restauração Firestore, chave LLM vazada, Jira fora do ar, custo disparado | revisão |
| F11-RT-10 | ZAP baseline scan sem achados altos | CI pré-GA |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Limites e operação

  Cenário: AT-F11-01 Cota diária                                # F11-RF-01, F11-RF-02
    Dado um usuário de teste com cota de 3 mensagens/dia
    Quando envio 3 mensagens
    Então o indicador mostra "3 de 3 mensagens hoje"
    Quando envio a 4ª
    Então vejo "Você atingiu o limite diário. Ele renova às 00:00 (horário de Brasília)."

  Cenário: AT-F11-02 Rate limit                                  # F11-RF-03
    Quando disparo 15 mensagens em 10 segundos pela API
    Então recebo 429 com Problem Details "rate_limited" a partir da 11ª

  Cenário: AT-F11-03 Alerta dispara                              # F11-RF-04
    Dado a revisão de ensaio que força 50% de erros 500 em dev
    Quando gero tráfego por 5 minutos
    Então o alerta "API 5xx > 2%" abre um incidente e envia e-mail

  Cenário: AT-F11-04 Requisição sem App Check é recusada em prd-like  # F11-RT-07
    Dado App Check em modo obrigatório
    Quando chamo a API com ID token válido e sem token App Check
    Então recebo 401 "app_check_required"
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| IX Observabilidade | Implementação direta |
| II Privacidade | `uid_hash` nos logs; sem conteúdo |
| VII Simplicidade | Sem Redis: contadores no Firestore + memória local |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F11-RF-01 | AT-F11-01 | ⬜ |
| F11-RF-02 | AT-F11-01 | ⬜ |
| F11-RF-03 | AT-F11-02 | ⬜ |
| F11-RF-04 | AT-F11-03 | ⬜ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
