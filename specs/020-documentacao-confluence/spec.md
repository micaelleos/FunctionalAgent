# F20 — Documentação do projeto no Confluence (escrita por ação proposta)

| Campo | Valor |
|---|---|
| **Status** | Em implementação |
| **Fase** | 4 — Evolução |
| **Responsável** | PO |
| **Dependências** | F19, F06, F10 |
| **ADRs relacionados** | ADR-009, ADR-003 |
| **Estimativa** | 6 dias |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md) ·
> [Metodologia](../../docs/metodologia/README.md) · [Modelos de página](../../docs/metodologia/modelos/README.md)

**Revisão 2026-11-20 (contra o código, antes da implementação):**
- **Tipos de ação:** `create_page`, `update_page` e `create_space`, no padrão de `create_issue`/`update_issue`. A confirmação da F06 despacha por tipo; a escrita no Confluence fica em `services/confluence_actions.py`.
- **Registro:** a conclusão grava `users/{uid}/documents/{pageId}` na mesma transação da ação, como a F10 faz com `jira_issues`.
- **Falha no meio da criação do espaço:** a ação vira `failed` com o código `confluence-partial` e a lista do que foi criado (sem status novo). Uma nova proposta completa o que falta.
- **"Create space" em Projects:** abre o chat com o projeto fixado e o pedido já escrito. A confirmação é o cartão de sempre, não uma segunda tela.
- **Ferramentas por turno:**
  - as de escrita só entram com `CONFLUENCE_WRITE_ENABLED` e o projeto vinculado;
  - `propor_criacao_espaco` só entra quando o projeto da conversa não tem espaço.
- **Espaço:** criado por `POST /wiki/rest/api/space` (v1, estável). As páginas usam a REST v2.
- **Modelos:** os 6 de `docs/metodologia/modelos/` são copiados para o backend, com teste de sincronia. Início, Arquitetura, Registro de mudanças e as páginas-pai "Decisões (ADR)" e "Features" têm esqueletos curtos no código.
- **ADR aceita:** a ferramenta recusa atualizar uma página de ADR com status "Aceito"; a mudança vira ADR nova.

---

## Parte A — Especificação (Gate 0)

### 1. Contexto e objetivo
- **Problema:** com a F19, o agente lê a documentação do projeto, mas ela ainda precisa existir. Escrever
  e manter Constituição, Glossário, Regras, ADRs, Roadmap e páginas de feature à mão faz a documentação
  ficar para trás do backlog.
- **Objetivo:** o agente cria o espaço a partir do [modelo](../../docs/metodologia/espaco-confluence.md) e
  escreve ou atualiza as páginas da metodologia a partir da conversa. Na fase Convergir, ele propõe
  alinhar o Roadmap e a página da feature com o que foi criado no Jira. Toda escrita passa por **ação
  proposta + Confirm** (Art. IV).
- **Indicador de sucesso:**
  - ≥ 50% dos épicos confirmados em projetos vinculados ganham página de feature no mesmo dia;
  - 0 escrita no Confluence sem confirmação (auditoria `confluence_write`);
  - 0 sobrescrita de edição alheia (conflitos de versão recusados).

### 2. Escopo
- **Inclui:**
  - criar o espaço com o modelo;
  - propor a criação e a atualização das páginas dos 8 tipos do modelo;
  - diff antes/depois na proposta;
  - controle de versão contra sobrescrita;
  - rótulos;
  - linha no "Registro de mudanças";
  - documentos criados na tela "Issues" (aba "Docs");
  - fase Convergir com escrita.
- **Fora de escopo:**
  - excluir, mover ou arquivar páginas;
  - permissões do espaço;
  - anexos e imagens;
  - comentários;
  - edição colaborativa em tempo real;
  - páginas fora do modelo (só leitura, F19).

### 3. Requisitos funcionais
| ID | Requisito | Prioridade |
|---|---|---|
| F20-RF-01 | Quando a F19 não acha espaço, o agente propõe criar o espaço (o botão "Create space" em Projects abre o chat do projeto com esse pedido) "<Projeto> — Documentação", com chave igual à do projeto quando livre, e a árvore do modelo (páginas com os modelos vazios e rótulos). Depois do Confirm, o espaço é criado e vinculado | Must |
| F20-RF-02 | O agente propõe **criar** uma página de um tipo do modelo (Constituição, Glossário, Regras de negócio, Arquitetura, ADR, Roadmap, Feature) a partir da conversa, no lugar certo da árvore, com os rótulos `specflow` e `specflow-tipo-<tipo>` | Must |
| F20-RF-03 | O agente propõe **atualizar** uma página existente; a proposta mostra o diff (antes/depois, por seção) e o resumo da mudança | Must |
| F20-RF-04 | Se a página mudou no Confluence depois da proposta, o Confirm falha com "This page changed since the proposal. Ask the agent to review it again." e nada é sobrescrito | Must |
| F20-RF-05 | Fase Convergir: depois de confirmar issues num projeto vinculado, o agente propõe atualizar o Roadmap (status e chave do épico) e a página da feature (tabela de decomposição com as chaves). Os IDs `RN-nn`, `ADR-nnn` e `FEAT-nn` novos seguem a numeração existente da página | Must |
| F20-RF-06 | Quando a conversa decide entre alternativas, o agente propõe uma ADR nova (Proposta) com contexto, decisão e alternativas; uma ADR aceita nunca é editada, só substituída (status "Substituída por ADR-nnn") | Should |
| F20-RF-07 | Cada escrita confirmada acrescenta uma linha no "Registro de mudanças" (data, página, resumo, "SpecFlow, confirmado por <nome>") na mesma confirmação | Should |
| F20-RF-08 | A tela "Issues" ganha a aba "Docs": páginas criadas ou atualizadas pelo SpecFlow, com link, tipo, data e status atual | Could |

### 4. Requisitos técnicos / não funcionais
| ID | Requisito | Como verificar |
|---|---|---|
| F20-RT-01 | As ferramentas `propor_criacao_pagina`, `propor_atualizacao_pagina` e `propor_criacao_espaco` só criam `ProposedAction` (`kind` = `create_page`, `update_page`, `create_space`); a execução fica em `services/confluence_actions.py`, chamada pela confirmação da F06, com o mesmo hash entre confirmado e executado (ADR-003) | `tests/unit/test_confluence_actions.py`, teste de hash |
| F20-RT-02 | Escrita: `POST /wiki/rest/api/space` (v1, `key`, `name`), `POST /wiki/api/v2/pages` (`spaceId`, `parentId`, `title`, `body.representation = storage`), `PUT /wiki/api/v2/pages/{id}` com `version.number = vista + 1`; rótulos por `POST /wiki/rest/api/content/{id}/label`. Sem retry em escrita; 409 → `confluence-version-conflict` | `tests/unit/test_confluence_client_write.py` (respx) |
| F20-RT-03 | Markdown → storage format determinístico (mesmas entradas, mesmo XHTML), escapando HTML do conteúdo; sem macros além de `info`/`status`/`toc` | `tests/unit/test_confluence_storage.py` (ida e volta com o conversor da F19) |
| F20-RT-04 | Diff por seção (títulos `##`) calculado no backend e guardado na proposta; o que o usuário vê é o que é executado | `tests/unit/test_page_diff.py` |
| F20-RT-05 | Os modelos de `docs/metodologia/modelos/` são a fonte dos esqueletos (copiados para `backend/app/agent/templates/confluence/` no build e conferidos por teste de igualdade) | `tests/unit/test_templates_in_sync.py` |
| F20-RT-06 | Auditoria `confluence_write` (`uid_hash`, tipo, `pageId`, resultado, ms), sem título nem conteúdo; métrica e painel | `tests/unit/test_telemetry.py` |
| F20-RT-07 | Registro dos documentos em `users/{uid}/documents/{pageId}` (`projectKey`, `spaceId`, `type`, `title`, `url`, `version`, `createdAt`, `updatedAt`) para a aba "Docs" | `tests/integration/test_documents_repo.py` |
| F20-RT-08 | Limites: ≤ 5 propostas de página por turno; página ≤ 50 mil caracteres em storage; criação do espaço é 1 ação (até 9 páginas) | testes das ferramentas |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Documentação no Confluence

  Cenário: AT-F20-01 Criar o espaço com o modelo                     # F20-RF-01
    Dado o projeto "SCRUM" sem espaço no Confluence
    Quando clico em "Create space" e confirmo a proposta
    Então o espaço existe com Início, Constituição, Glossário, Regras de negócio, Arquitetura, Decisões (ADR), Roadmap, Features e Registro de mudanças
    E o projeto "SCRUM" aparece vinculado ao espaço

  Cenário: AT-F20-02 Constituição escrita a partir da conversa        # F20-RF-02, F20-RF-07
    Dado o espaço vinculado
    Quando digo "vamos escrever a constituição: dados de clientes nunca saem do Brasil"
    E confirmo a proposta de página
    Então a página "Constituição" tem o artigo com essa regra e a versão 1.0.0
    E o "Registro de mudanças" tem uma linha nova

  Cenário: AT-F20-03 Roadmap acompanha o épico criado                 # F20-RF-05, F20-RF-03
    Dado um épico confirmado no Jira a partir de uma conversa do projeto
    Então o agente propõe atualizar "Roadmap" e criar a página da feature, mostrando o diff
    Quando confirmo
    Então o Roadmap tem a linha da feature com a chave do épico

  Cenário: AT-F20-04 Não sobrescreve edição de outra pessoa           # F20-RF-04
    Dado uma proposta de atualização da página "Glossário"
    E alguém editou o "Glossário" no Confluence depois da proposta
    Quando clico em "Confirm"
    Então vejo "This page changed since the proposal. Ask the agent to review it again."
    E a página mantém a edição da outra pessoa

  Cenário: AT-F20-05 Nada é escrito sem Confirm                       # F20-RT-01
    Quando o agente propõe uma página e eu clico em "Discard"
    Então nenhuma página nova existe no espaço
```

### 6. Conformidade com a Constituição
| Artigo | Como esta feature cumpre | Exceção? |
|---|---|---|
| II Privacidade | Registro de documentos sob `users/{uid}`; conteúdo das páginas não é guardado no Firestore (só metadados) | Não |
| III Segredos | Credencial da F04; nada novo | Não |
| IV Humano no controle | Toda escrita é ação proposta; hash confirmado = executado; versão da página contra sobrescrita; sem exclusão | Não |
| V Contrato | `kind` novos de ação proposta e eventos SSE definidos na Fase 1 | Não |
| VI Testes | respx para escrita; AT-F20-01..05 no sandbox; ida e volta do conversor | Não |
| VII Simplicidade | Sem infra nova | Não |
| XI Qualidade do agente | Evals de quando propor documentação (sem excesso de propostas) | Não |

---

## Parte C — Validação (Gates 3 e 4)

### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F20-RF-01 | AT-F20-01, `tests/unit/test_confluence_actions.py` | ⬜ |
| F20-RF-02 | AT-F20-02, `tests/unit/test_confluence_page_tools.py` | ⬜ |
| F20-RF-03 | AT-F20-03, `tests/unit/test_page_diff.py` | ⬜ |
| F20-RF-04 | AT-F20-04, `tests/unit/test_confluence_client_write.py` | ⬜ |
| F20-RF-05 | AT-F20-03, evals `confluence-converge-write-*` | ⬜ |
| F20-RF-06 | evals `confluence-adr-*` | ⬜ |
| F20-RF-07 | AT-F20-02, `tests/unit/test_confluence_actions.py` | ⬜ |
| F20-RF-08 | `IssuesPage.test.tsx` | ⬜ |

### 11. Evidências
| Data | Versão/commit | Ambiente | Execução (link CI) | Resultado | Aceito por |
|---|---|---|---|---|---|
| | | | | | |
