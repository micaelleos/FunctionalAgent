# F17 — Contexto do repositório (GitHub, só leitura)

| Campo | Valor |
|---|---|
| **Status** | Rascunho (Fase 4 — detalhar plano técnico após GA) |
| **Fase** | 4 — Evolução |
| **Dependências** | F05, F12 |
| **ADRs** | ADR-007 (novo ADR para o app GitHub antes do Gate 1) |
| **Estimativa** | 5 dias |

> [Spec](spec.md) · [Roadmap](../ROADMAP.md) · [Doc 10 — Specs para agentes](../../docs/modernizacao/10-specs-para-agentes.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** sem conhecer o código, o agente do SpecFlow não consegue dizer ao agente de código **onde** mexer, e
  a pesquisa associa a localização (módulos, arquivos) a mais PRs aceitos (doc 10 §3).
- **Objetivo:** o PO conecta um repositório GitHub em modo leitura; o agente usa `AGENTS.md`/`CLAUDE.md`, a
  estrutura de pastas e buscas no código para preencher a seção "Onde mexer" e respeitar as convenções do projeto.
- **Indicador:** % de specs `agent-ready` com "Onde mexer" preenchida; nota de contexto na rubrica das evals (F15).

### 2. Escopo
- **Inclui:** GitHub App com permissão só de leitura (`contents:read`, `metadata:read`) instalado pelo PO em
  repositórios escolhidos; vínculo projeto do Jira ↔ repositório; ferramentas de leitura do agente (ler
  `AGENTS.md`/`CLAUDE.md`, listar árvore, buscar texto, ler arquivo com limite de tamanho); seção "Onde mexer".
- **Fora de escopo:** escrever no repositório (a F18 cria PR só com specs), GitLab/Bitbucket, indexação vetorial.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F17-RF-01 | O PO conecta repositórios pelo GitHub App, escolhendo quais, e vincula cada um a um projeto do Jira | Must |
| F17-RF-02 | Ao escrever uma spec para um projeto vinculado, o agente lê as instruções do repositório (`AGENTS.md`, `CLAUDE.md`) e as convenções de teste | Must |
| F17-RF-03 | A seção "Onde mexer" lista módulos/arquivos prováveis com o motivo de cada um, e "Como verificar" usa os comandos de teste do repositório | Must |
| F17-RF-04 | O PO pode desconectar um repositório; o SpecFlow apaga o vínculo e não guarda cópia do código | Must |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F17-RT-01 | Token de instalação do GitHub App de curta duração, gerado por requisição; chave privada do App no Secret Manager | revisão + unit |
| F17-RT-02 | Leitura limitada (arquivo ≤ 100 KB, ≤ 20 arquivos por turno, busca ≤ 50 resultados) e conteúdo do repositório tratado como dado não confiável | unit + eval de injeção |
| F17-RT-03 | Nenhum conteúdo de código persistido além da mensagem do turno | integração |

### 5. Teste final de aceitação
```gherkin
  Cenário: AT-F17-01 "Onde mexer" a partir do repositório         # F17-RF-02, F17-RF-03
    Dado o repositório de exemplo vinculado ao projeto "E2E" com um AGENTS.md que manda rodar "make test"
    Quando peço uma story para validar CPF no cadastro
    Então a spec proposta tem "Onde mexer" citando o módulo de cadastro
    E "Como verificar" cita "make test"

  Cenário: AT-F17-02 Desconectar                                  # F17-RF-04
    Quando desconecto o repositório
    Então as próximas specs do projeto "E2E" não têm "Onde mexer" preenchida
```

### 6. Conformidade com a Constituição
II (vínculos em `users/{uid}`), III (chave do App no Secret Manager), IV (só leitura), VII (novo integrador exige ADR),
XII (localização melhora a prontidão para agentes).
