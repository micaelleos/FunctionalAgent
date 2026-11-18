# F11 — Observabilidade, limites de uso e proteção

| Campo | Valor |
|---|---|
| **Status** | Rascunho |
| **Fase** | 3 — Produção |
| **Dependências** | F05–F10 |
| **Estimativa** | 6 dias |
| **Revisão** | 2026-11-18: contra o código em produção e as decisões do PO — um só PR; cota de 20 mensagens e 200 mil tokens/dia; rate limit sem estado em memória (Art. II.3); alerta de custo estimado no lugar do budget (F02-RT-09); ambiente único: App Check em "monitor" em prd e "obrigatório" depois de 1 semana; descoberto que os logs `info` (`chat_turn`, auditoria `jira_write` da F06) não chegam ao Cloud Logging |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** sem logs estruturados, métricas, alertas nem controle de custo de LLM (D03, D17).
- **Objetivo:** operar com visibilidade (SLOs, alertas, dashboard), custo previsível (cotas) e proteção contra abuso (App Check).
- **Indicador:** SLOs medidos: disponibilidade 99,5%, p95 de turno < 30 s, primeiro token p75 < 3 s.

### 2. Escopo
- **Inclui:** logging estruturado com correlação, traces OpenTelemetry, métricas de negócio (log-based metrics),
  dashboard, alertas, SLO de disponibilidade, cotas diárias por usuário, App Check, rate limit por usuário, erros do
  front, teste de carga, varredura ZAP, runbooks.
- **Ambiente:** o app tem só produção (ADR-006). Os ensaios de alerta e de App Check obrigatório rodam em prd de forma
  controlada (revisão sem tráfego / modo `monitor`), nunca tocando recursos de outros apps (F02-RT-09).
- **Fora de escopo:** painel administrativo de usuários; billing para usuários.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F11-RF-01 | O usuário vê seu consumo do dia (mensagens) e o limite, e o histórico dos últimos 7 dias em "My account" | Should |
| F11-RF-02 | Ao atingir a cota diária (mensagens ou tokens), o envio é recusado antes de chamar o modelo, com mensagem clara e o horário de renovação (00:00 de Brasília) | Must |
| F11-RF-03 | Mensagens em excesso (rate limit) recebem "Too many messages. Wait N seconds and try again."; a mensagem não conta na cota | Must |
| F11-RF-04 | O responsável recebe alerta (e-mail) em erro elevado, latência alta, falha de LLM/Jira, API fora do ar e custo estimado de LLM acima do limite diário | Must |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F11-RT-01 | Logs JSON em uma linha no formato do Cloud Logging: `severity`, `message`, `logging.googleapis.com/trace`, `request_id`, `uid_hash` (SHA-256 truncado, nunca o `uid`); nível INFO da app ligado (hoje `chat_turn` e `jira_write` se perdem); sem conteúdo de mensagens nem segredos | unit |
| F11-RT-02 | Traces OpenTelemetry → Cloud Trace: span do request (contexto do header do Cloud Run), spans do turno do agente, de cada chamada ao Jira (httpx) e ao modelo; ligado por `TRACING_ENABLED` (prd), amostragem do pai | unit + verificação em prd |
| F11-RT-03 | Métricas por log (Terraform): turnos, tokens, custo estimado, latência do turno e do 1º token, ações propostas/confirmadas/falhas, erros do Jira por código, cota e rate limit atingidos; dashboard `specflow` | `terraform validate` + dashboard |
| F11-RT-04 | Alertas (Terraform, canal de e-mail): 5xx > 2% em 5 min, p95 do turno > 30 s, erro do modelo > 5%, falhas de Jira, uptime check `/health` falhando, custo estimado > `daily_cost_alert_usd`/dia. E-mail só por variável no apply (repo público); SLO de disponibilidade 99,5% (28 dias) | `terraform validate` + AT-F11-03 |
| F11-RT-05 | Cota diária configurável (`DAILY_MESSAGE_QUOTA`=20, `DAILY_TOKEN_QUOTA`=200000) em `users/{uid}/usage/{dia de Brasília}`, reservada numa transação antes de chamar o modelo; tokens somados ao fim do turno | unit + integração |
| F11-RT-06 | Rate limit por `uid`: 10 mensagens em 60 s (janela deslizante guardada no documento de uso, na mesma transação da cota; sem estado em memória, Art. II.3); 429 `rate-limited` com `Retry-After` | unit + integração |
| F11-RT-07 | App Check: o SPA manda `X-Firebase-AppCheck` (reCAPTCHA Enterprise); o backend verifica com `APP_CHECK_MODE` = `off` (local/test), `monitor` (só registra) ou `enforce` (401 `app-check-required`). Sai em `monitor` e vira `enforce` após 1 semana sem falsos negativos. Sem enforcement nos serviços do Firebase do projeto (compartilhado) | unit + integração |
| F11-RT-08 | Teste de carga (k6): 50 usuários simultâneos com LLM fake contra a API local, erro < 1%, p95 do overhead do backend < 500 ms | k6 |
| F11-RT-09 | Runbooks: rollback (existe), restauração do Firestore, credencial vazada (token Jira, SA), Jira fora do ar, custo disparado, cota e App Check | revisão |
| F11-RT-10 | ZAP baseline no SPA e na API de prd sem achados altos | workflow `zap.yml` |
| F11-RT-11 | Erros de front (vindo da F08-RT-07): `POST /api/v1/client-errors` (sem login obrigatório, corpo limitado) → log no formato do Error Reporting, sem conteúdo das mensagens; o SPA reporta `error`, `unhandledrejection` e erros de renderização, no máximo 5 por página | unit + Vitest |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Limites e operação

  Cenário: AT-F11-01 Cota diária                                # F11-RF-01, F11-RF-02
    Dado a API com cota de 3 mensagens/dia
    Quando envio 3 mensagens
    Então o indicador mostra "3 of 3"
    Quando envio a 4ª
    Então vejo "You've reached today's limit. It renews at 00:00 (Brasília time)."

  Cenário: AT-F11-02 Rate limit                                  # F11-RF-03
    Quando disparo 15 mensagens em 10 segundos pela API
    Então recebo 429 com Problem Details "rate-limited" e Retry-After a partir da 11ª

  Cenário: AT-F11-03 Alerta dispara                              # F11-RF-04
    Dado as políticas de alerta aplicadas em prd
    Quando o uptime check aponta para uma rota que falha por 5 minutos (ensaio)
    Então o alerta abre um incidente e envia e-mail ao responsável

  Cenário: AT-F11-04 Requisição sem App Check é recusada com "enforce"  # F11-RT-07
    Dado App Check em modo obrigatório
    Quando chamo a API com ID token válido e sem token App Check
    Então recebo 401 "app-check-required"
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| IX Observabilidade | Implementação direta |
| II Privacidade | `uid_hash` nos logs; sem conteúdo |
| VII Simplicidade | Sem Redis: cota e rate limit no mesmo documento do Firestore, numa transação |
| II.3 Sem estado por usuário em memória | Rate limit no Firestore, não em memória da instância |
| F02-RT-09 Projeto compartilhado | Recursos `specflow-*`; sem budget, sem enforcement de App Check nos serviços do projeto |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F11-RF-01 | AT-F11-01, `test_usage.py`, `UsagePanel.test.tsx`, `http.test.ts` | ⬜ |
| F11-RF-02 | AT-F11-01, `test_usage.py`, `ChatPage.test.tsx` | ⬜ |
| F11-RF-03 | AT-F11-02, `test_usage.py`, `ChatPage.test.tsx` | ⬜ |
| F11-RF-04 | AT-F11-03, `infra/terraform/modules/monitoring` | ⬜ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
