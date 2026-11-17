# F09 — Projetos Jira

| Campo | Valor |
|---|---|
| **Status** | Aceita |
| **Fase** | 2 — Produto |
| **Dependências** | F04, F08 |
| **Estimativa** | 3 dias |
| **Revisão** | 2026-11-17: total de issues pelo `expand=insight` da busca de projetos (sem chamada por projeto); abertas por `search/approximate-count`; cache no Firestore em vez de memória (Art. II.3); link `/browse/KEY` (vale para qualquer tipo de projeto); avatar do Jira com iniciais de reserva |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** a página atual faz uma chamada ao Jira por projeto a cada renderização (D14) e constrói links frágeis.
- **Objetivo:** lista rápida dos projetos do usuário com acesso direto ao Jira e atalho para conversar sobre o projeto.
- **Indicador:** p95 de `GET /jira/projects` < 1,5 s.

### 2. Escopo
- **Inclui:** lista em cards (avatar, nome, chave, tipo, issues abertas e total), busca por nome/chave, "Abrir no
  Jira", "Conversar sobre este projeto" (cria conversa com projeto fixado — F07-RF-06), "Atualizar" (ignora o cache).
  A tela já existe (F08, T008) com dados de demonstração; aqui ela passa a usar a API real.
- **Fora de escopo:** board/sprints, métricas do projeto.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F09-RF-01 | O usuário vê todos os projetos que pode acessar no Jira, com avatar (iniciais se a imagem não carregar), nome, chave e tipo | Must |
| F09-RF-02 | Cada projeto mostra as issues abertas e o total; a contagem que falhar aparece como "—" | Should |
| F09-RF-03 | O usuário filtra projetos digitando parte do nome ou da chave | Should |
| F09-RF-04 | "Abrir no Jira" abre o projeto em nova aba | Must |
| F09-RF-05 | "Conversar sobre este projeto" abre uma conversa nova com o projeto fixado | Should |
| F09-RF-06 | Sem conexão Jira, a página orienta a conectar; se o Jira recusar o token guardado, a conexão fica inválida e a página orienta a trocar o token | Must |
| F09-RF-07 | "Atualizar" busca de novo no Jira, ignorando o cache | Could |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F09-RT-01 | Total de issues pelo `expand=insight` de `project/search`; abertas (`statusCategory != Done`) por `POST /rest/api/3/search/approximate-count`, em paralelo com concorrência máxima 5. Resultado em cache por usuário por 5 min no Firestore (`users/{uid}/cache/jiraProjects`, nunca na memória do processo — Art. II.3), invalidado se a conexão (id ou site) mudar | unit |
| F09-RT-02 | Links montados no backend a partir da `siteUrl` normalizada: `<site>/browse/<KEY>` | unit |
| F09-RT-03 | Paginação de `/rest/api/3/project/search` até `isLast`, com teto de 20 páginas (1000 projetos) | unit com transporte falso |
| F09-RT-04 | Falha na contagem de um projeto não quebra a lista (mostra "—") | unit |
| F09-RT-05 | Erros: sem conexão → 409 `jira-not-connected`; 401/403 do Jira → conexão marcada inválida e 409 `jira-credential-rejected`; Jira fora do ar → 502 `jira-unreachable` | unit |
| F09-RT-06 | p95 de `GET /api/v1/jira/projects` < 1,5 s (indicador) | integração com Jira falso (latência simulada) |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Projetos Jira

  Cenário: AT-F09-01 Listar e filtrar                           # F09-RF-01, F09-RF-02, F09-RF-03
    Dado que estou conectado ao Jira sandbox
    Quando abro "Jira projects"
    Então vejo o card do projeto do sandbox com as issues abertas e o total
    Quando digito parte da chave no filtro
    Então vejo só os projetos que batem, e com um texto sem correspondência vejo o aviso de nenhum resultado

  Cenário: AT-F09-02 Abrir no Jira e conversar                  # F09-RF-04, F09-RF-05
    Quando vejo "Open in Jira" no card do projeto
    Então o link aponta para "<site>/browse/<KEY>" e abre em nova aba com rel seguro
    Quando clico em "Chat about this project"
    Então abre uma conversa nova com o selo "Pinned project: <KEY>"

  Cenário: AT-F09-03 Sem conexão                                 # F09-RF-06
    Dado um usuário sem conexão Jira
    Quando abro "Jira projects"
    Então vejo "Jira not connected" com link para Configurações
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| II Privacidade | Cache em `users/{uid}/cache` (Firestore, só backend), 5 min; nada na memória do processo; apagado com a conta (exclusão recursiva da F03) |
| IV Human-in-the-loop | Só leitura no Jira |
| X UX | Estado vazio orientado |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F09-RF-01 | AT-F09-01, `test_jira_projects.py`, `ProjectsPage.test.tsx`, `http.test.ts` | ✅ |
| F09-RF-02 | AT-F09-01, `test_jira_projects.py`, `ProjectsPage.test.tsx` | ✅ |
| F09-RF-03 | AT-F09-01, `ProjectsPage.test.tsx` | ✅ |
| F09-RF-04 | AT-F09-02, `test_jira_projects.py`, `ProjectsPage.test.tsx` | ✅ |
| F09-RF-05 | AT-F09-02, `ProjectsPage.test.tsx` | ✅ |
| F09-RF-06 | AT-F09-03, `test_jira_projects.py`, `ProjectsPage.test.tsx` | ✅ |
| F09-RF-07 | `test_jira_projects.py`, `ProjectsPage.test.tsx`, `http.test.ts` | ✅ |
| F09-RT-01 | `test_jira_projects.py` (concorrência ≤ 5, cache de 5 min, outra conexão) | ✅ |
| F09-RT-02 | `test_jira_projects.py` (`/browse/KEY`) | ✅ |
| F09-RT-03 | `test_jira_projects.py` (paginação até `isLast`, teto de páginas) | ✅ |
| F09-RT-04 | `test_jira_projects.py`, `ProjectsPage.test.tsx` ("—") | ✅ |
| F09-RT-05 | `test_jira_projects.py`, `jira.test.tsx` (aviso de reconectar) | ✅ |
| F09-RT-06 | `test_jira_projects_perf.py` | ✅ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
| 2026-11-17 | `feat/F09-projetos-jira` | Local: Vite + API + emuladores, Jira sandbox `SCRUM` só leitura | `E2E_EMULATORS=1 npx playwright test e2e/f09-projetos.spec.ts` (e a suíte local inteira) | AT-F09-01..03 2/2 (o projeto do sandbox com abertas e total, filtro, sem resultado, `/browse/SCRUM` em nova aba, Refresh, chat com o projeto fixado; sem conexão orienta a conectar); suíte local 19/19 | PO (aceite com as evidências locais) |
| 2026-11-17 | `feat/F09-projetos-jira` | Unit, Jira falso com 150 ms por chamada, 20 projetos | `test_jira_projects_perf.py` | p95 < 1,5 s (cache frio ≈ 6 × 150 ms; com cache, sem chamadas ao Jira) | PO (aceite com as evidências locais) |
