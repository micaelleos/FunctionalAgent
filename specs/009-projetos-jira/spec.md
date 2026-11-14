# F09 — Projetos Jira

| Campo | Valor |
|---|---|
| **Status** | Rascunho |
| **Fase** | 2 — Produto |
| **Dependências** | F04, F08 |
| **Estimativa** | 3 dias |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** a página atual faz uma chamada ao Jira por projeto a cada renderização (D14) e constrói links frágeis.
- **Objetivo:** lista rápida dos projetos do usuário com acesso direto ao Jira e atalho para conversar sobre o projeto.
- **Indicador:** p95 de `GET /jira/projects` < 1,5 s.

### 2. Escopo
- **Inclui:** lista em cards (avatar, nome, chave, tipo, contagem de issues), busca por nome/chave, "Abrir no Jira",
  "Conversar sobre este projeto" (cria conversa com projeto fixado — F07-RF-06).
- **Fora de escopo:** board/sprints, métricas do projeto.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F09-RF-01 | O usuário vê todos os projetos que pode acessar no Jira, com avatar, nome e chave | Must |
| F09-RF-02 | Cada projeto mostra a quantidade de issues | Should |
| F09-RF-03 | O usuário filtra projetos digitando parte do nome ou da chave | Should |
| F09-RF-04 | "Abrir no Jira" abre o projeto em nova aba | Must |
| F09-RF-05 | "Conversar sobre este projeto" abre uma conversa nova com o projeto fixado | Should |
| F09-RF-06 | Sem conexão Jira, a página orienta a conectar | Must |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F09-RT-01 | Contagens obtidas com chamadas paralelas limitadas (concorrência 5) e cache por usuário de 5 min | unit |
| F09-RT-02 | Links montados no backend a partir da `siteUrl` normalizada | unit |
| F09-RT-03 | Paginação dos projetos do Jira (`/rest/api/3/project/search`) até o fim | unit com respx |
| F09-RT-04 | Falha na contagem de um projeto não quebra a lista (mostra "—") | unit |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Projetos Jira

  Cenário: AT-F09-01 Listar e filtrar                           # F09-RF-01, F09-RF-02, F09-RF-03
    Dado que estou conectado ao Jira sandbox com os projetos "E2E" e "DEMO"
    Quando abro "Projetos"
    Então vejo os cards "E2E" e "DEMO" com contagem de issues
    Quando digito "dem" no filtro
    Então vejo apenas "DEMO"

  Cenário: AT-F09-02 Abrir no Jira e conversar                  # F09-RF-04, F09-RF-05
    Quando clico em "Abrir no Jira" em "E2E"
    Então uma nova aba abre "<site>/jira/software/projects/E2E/issues"
    Quando clico em "Conversar sobre este projeto"
    Então abre uma conversa nova com o selo "Projeto: E2E"

  Cenário: AT-F09-03 Sem conexão                                 # F09-RF-06
    Dado um usuário sem conexão Jira
    Quando abro "Projetos"
    Então vejo "Conecte sua conta do Jira" com link para Configurações
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| II Privacidade | Cache por `uid`, em memória por instância com TTL curto (sem dados persistidos) |
| X UX | Estado vazio orientado |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F09-RF-01 | AT-F09-01 | ⬜ |
| F09-RF-02 | AT-F09-01 | ⬜ |
| F09-RF-03 | AT-F09-01 | ⬜ |
| F09-RF-04 | AT-F09-02 | ⬜ |
| F09-RF-05 | AT-F09-02 | ⬜ |
| F09-RF-06 | AT-F09-03 | ⬜ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
