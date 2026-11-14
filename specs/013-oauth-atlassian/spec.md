# F13 — Login Atlassian via OAuth 2.0 (3LO)

| Campo | Valor |
|---|---|
| **Status** | Rascunho (Fase 4 — detalhar plano técnico após GA) |
| **Fase** | 4 — Evolução |
| **Dependências** | F04, F12 |
| **ADRs** | ADR-004 |
| **Estimativa** | 7 dias |

> [Spec](spec.md) · [Plano](plan.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** gerar e colar API token é a maior fricção do onboarding e o token tem todos os poderes do usuário.
- **Objetivo:** botão "Conectar com Atlassian", com escopos mínimos, revogável, sem token manual.
- **Indicador:** taxa de conclusão do onboarding (login → conexão Jira ok) ≥ 80%.

### 2. Escopo
- **Inclui:** app OAuth no Atlassian Developer Console, fluxo authorization code + PKCE via backend, escolha do site
  (`accessible-resources` → `cloudid`), refresh token cifrado (KMS), chamadas via `api.atlassian.com/ex/jira/{cloudid}`.
- **Fora de escopo:** remover a opção de API token (permanece como alternativa).

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F13-RF-01 | O usuário conecta o Jira clicando em "Conectar com Atlassian" e autorizando na Atlassian | Must |
| F13-RF-02 | Com acesso a vários sites, o usuário escolhe qual usar | Must |
| F13-RF-03 | A conexão se mantém sem novo login até o usuário revogar | Must |
| F13-RF-04 | O usuário pode desconectar; o app revoga/descarta os tokens | Must |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F13-RT-01 | Escopos mínimos: `read:jira-work`, `write:jira-work`, `read:jira-user`, `offline_access` | revisão |
| F13-RT-02 | `state` assinado + PKCE; callback valida origem e `uid` | unit |
| F13-RT-03 | Refresh token rotativo cifrado com KMS; renovação automática transparente | integração |
| F13-RT-04 | `JiraClient` abstrai Basic vs OAuth (mesma interface para as ferramentas) | unit |

### 5. Teste final de aceitação
```gherkin
  Cenário: AT-F13-01 Conectar via OAuth                          # F13-RF-01, F13-RF-03
    Dado um usuário sem conexão Jira
    Quando clico em "Conectar com Atlassian" e autorizo com a conta sandbox
    Então volto ao app com "Conectado como <nome>"
    E no dia seguinte (simulado com expiração do access token) "Projetos" carrega sem novo login

  Cenário: AT-F13-02 Múltiplos sites                              # F13-RF-02
    Dado uma conta Atlassian com 2 sites
    Quando autorizo
    Então escolho o site e a conexão usa o site escolhido

  Cenário: AT-F13-03 Desconectar                                  # F13-RF-04
    Quando desconecto
    Então "Projetos" pede conexão e o token salvo foi apagado
```

### 6. Conformidade com a Constituição
III (tokens cifrados, nunca no cliente), IV (confirmação humana continua obrigatória).
