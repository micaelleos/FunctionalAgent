# ADR-007 — Specs prontas para agentes de IA de código: esquema estruturado, seções fixas e prontidão verificada

- **Status:** Proposto · **Data:** 2026-11-16
- **Requisitos:** [10 — Specs para agentes](../10-specs-para-agentes.md) · **Emenda:** Constituição v2.1.0 (Artigo XII)

## Contexto

O PO decidiu que as issues criadas pelo SpecFlow AI devem ser escritas para **agentes de IA de código** lerem e
implementarem (Claude Code, Copilot, Cursor, Codex, Rovo Dev). Esses agentes já leem o Jira pelo MCP oficial da
Atlassian. A evidência disponível (doc 10, §3) indica que o resultado melhora com escopo pequeno, spec autocontida,
critérios de aceite explícitos com casos de borda e corpo enxuto. Hoje o agente gera Markdown livre a partir do
prompt; a qualidade depende do modelo e não é verificável.

## Opções

| Opção | Verificável | Esforço | Risco |
|---|---|---|---|
| A. Só ajustar o prompt para escrever "no formato" | Não (regex frágil) | Baixo | Deriva silenciosa a cada mudança de modelo |
| B. **Esquema estruturado** (`AgentReadySpec`, Pydantic) como argumento das ferramentas; ADF renderizado do esquema; verificação determinística | Sim | Médio | Esquema pode engessar casos raros |
| C. Campos customizados no Jira (um por seção) | Sim | Alto | Exige admin do Jira; nem todo agente lê campos customizados |
| D. Exportar specs só para o repositório (Spec Kit) | Sim | Médio | Tira o Jira do centro, onde o PO trabalha |

## Decisão

**Opção B**, com o Jira como canal no MVP e o repositório como evolução (F18).

- As ferramentas de escrita do agente (`propor_criacao_issue`, `propor_atualizacao_issue`) recebem um
  `AgentReadySpec` (tipo, título, seções da doc 10 §4.2, cenários com ID e tipo, dependências, perguntas em aberto),
  validado por Pydantic. O payload da ação proposta (ADR-003) é esse objeto.
- O renderizador gera ADF (Jira API v3) e Markdown com **seções fixas, mesma ordem e mesmos títulos**. O hash
  conferido na confirmação é o do objeto canônico; o ADF é derivado.
- A verificação de prontidão (regras P-01 a P-10) é uma função pura, sem LLM, executada na proposta e na edição
  (F14). Ela **avisa, não bloqueia**; a label `agent-ready` só é aplicada quando todas as regras obrigatórias passam.
- Labels: `specflow` sempre; `agent-ready` quando pronta; `human-only` quando o agente do SpecFlow indicar que a
  mudança não é recomendada para agente de código.
- Títulos das seções em pt-BR fixos no MVP.

## Consequências

- ✅ Formato testável em unidade (esquema, renderizador, regras) e medido nas evals (F15).
- ✅ Funciona com qualquer agente que leia o Jira; nada específico de fornecedor.
- ✅ Edição antes de confirmar (F14) passa a ser por seção, mantendo o contrato.
- ⚠️ O esquema precisa de uma saída para casos que não cabem (ex.: spike de pesquisa): tipo `Tarefa` com
  seções opcionais e sem `agent-ready`.
- ⚠️ Specs ricas tendem a crescer; a regra P-09 limita o corpo a ~600 palavras como aviso.
- ⚠️ Atualiza o ADR-003: o payload proposto deixa de ser "summary/description livres" e passa a ser o esquema.
