# F18 — Exportar specs para o repositório (formato Spec Kit)

| Campo | Valor |
|---|---|
| **Status** | Rascunho (Fase 4 — detalhar plano técnico após GA) |
| **Fase** | 4 — Evolução |
| **Dependências** | F06, F17 |
| **ADRs** | ADR-007 |
| **Estimativa** | 4 dias |

> [Spec](spec.md) · [Roadmap](../ROADMAP.md) · [Doc 10 — Specs para agentes](../../docs/modernizacao/10-specs-para-agentes.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** parte dos times prefere specs versionadas junto do código (Spec Kit, Kiro), onde o agente de código
  as encontra sem passar pelo Jira.
- **Objetivo:** o PO exporta um épico e suas histórias para o repositório conectado como arquivos Markdown no formato
  Spec Kit, por meio de um PR que o time revisa.
- **Indicador:** PRs de spec abertos e mesclados por mês.

### 2. Escopo
- **Inclui:** geração de `specs/<nnn-slug>/spec.md` (e `tasks.md` a partir das histórias) a partir do `AgentReadySpec`;
  branch e PR no repositório (permissão adicional `contents:write` e `pull_requests:write`, pedida só para isso);
  link entre a issue do Jira e o arquivo; confirmação humana antes de abrir o PR (Artigo IV).
- **Fora de escopo:** sincronização bidirecional Jira ↔ repositório; outros formatos além de Spec Kit no MVP.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F18-RF-01 | O PO escolhe um épico criado pelo SpecFlow e vê a prévia dos arquivos que serão gerados | Must |
| F18-RF-02 | Ao confirmar, o SpecFlow abre um PR no repositório com os arquivos e o link para as issues do Jira | Must |
| F18-RF-03 | Os arquivos seguem as seções fixas do contrato (doc 10 §4.2) e os IDs dos critérios de aceite (`CA-nn`) | Must |
| F18-RF-04 | A issue do Jira recebe um link para o arquivo no PR | Should |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F18-RT-01 | Abrir PR é uma ação proposta (ADR-003): payload com os arquivos e hash conferido na execução | unit |
| F18-RT-02 | Nunca escreve na branch padrão; só cria a branch `specflow/<chave>` e o PR | integração com repositório de teste |

### 5. Teste final de aceitação
```gherkin
  Cenário: AT-F18-01 Exportar épico como PR                        # F18-RF-01, F18-RF-02, F18-RF-03
    Dado o épico "E2E-10" com 2 histórias criadas pelo SpecFlow
    Quando exporto para o repositório de exemplo e confirmo
    Então existe um PR com "specs/<nnn>-<slug>/spec.md" e "tasks.md"
    E o spec.md tem as seções "Objetivo", "Critérios de aceite" e "Fora de escopo" de cada história
```

### 6. Conformidade com a Constituição
IV (PR só após confirmação), XII (mesmo contrato do Jira).
