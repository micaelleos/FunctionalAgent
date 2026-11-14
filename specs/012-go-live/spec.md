# F12 — Go-live e desativação do Streamlit

| Campo | Valor |
|---|---|
| **Status** | Rascunho |
| **Fase** | 3 — Produção |
| **Dependências** | F01–F11 |
| **Estimativa** | 3 dias |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Objetivo:** colocar o novo app em produção para todos os usuários, comunicar a mudança e remover o Streamlit.
- **Indicador:** 0 incidentes Sev1 na primeira semana; 100% dos usuários beta migrados.

### 2. Escopo
- **Inclui:** checklist de prontidão, beta fechado, domínio próprio (se decidido), comunicação, redirecionamento do
  endereço antigo, remoção de `legacy/`, tag `legacy-streamlit-final`, README novo.
- **Fora de escopo:** migração de dados do Streamlit (não há dados persistidos).

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F12-RF-01 | Todas as capacidades do app antigo existem no novo (matriz de paridade abaixo) | Must |
| F12-RF-02 | Quem acessar o endereço antigo é levado ao novo app | Should |
| F12-RF-03 | A página "Sobre"/ajuda explica o novo fluxo (login, conectar Jira, confirmar ações) | Must |

**Matriz de paridade**

| Capacidade antiga | Onde está no novo | Teste |
|---|---|---|
| Chat com agente | F05 + F08 | AT-F05-01, AT-F08-01 |
| Criar issue no Jira | F05 + F06 | AT-F06-01 |
| Atualizar issue | F06 | AT-F06-05 |
| Consultar issue / JQL / projetos | F05 | AT-F05-03 |
| Lista de projetos | F09 | AT-F09-01 |
| Issues criados | F10 | AT-F10-01 |
| Configurar credenciais Jira | F04 | AT-F04-01 |
| Página Sobre | F08 / F04-RF-07 | revisão |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F12-RT-01 | Checklist de prontidão (abaixo) 100% marcado | revisão |
| F12-RT-02 | Suíte E2E completa verde em prd com conta de teste (somente leitura + projeto sandbox) | CI |
| F12-RT-03 | `legacy/` removido; nenhuma dependência Streamlit no repo | `grep` no CI |

**Checklist de prontidão:** SLOs e alertas ativos (F11) · backups e restauração testados · runbooks revisados ·
evals ≥ baseline · ZAP sem achados altos · custo estimado aprovado · política de privacidade/termos publicados ·
App Check obrigatório · domínio e HTTPS (se aplicável) · contatos de suporte na página Sobre.

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Go-live

  Cenário: AT-F12-01 Jornada completa em produção               # F12-RF-01, F12-RT-02
    Dado uma conta de teste em produção conectada ao Jira sandbox
    Quando faço login, peço um épico e uma story para o projeto "E2E" e confirmo as duas ações
    Então os dois issues existem no Jira
    E aparecem em "Issues criados"
    E a conversa está disponível após sair e entrar de novo

  Cenário: AT-F12-02 Endereço antigo redireciona                 # F12-RF-02
    Quando acesso o endereço do app Streamlit
    Então sou redirecionado para o novo app
```

### 6. Conformidade com a Constituição
Validação final de todos os artigos via checklist de prontidão.

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F12-RF-01 | Matriz de paridade, AT-F12-01 | ⬜ |
| F12-RF-02 | AT-F12-02 | ⬜ |
| F12-RF-03 | Revisão do PO | ⬜ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
