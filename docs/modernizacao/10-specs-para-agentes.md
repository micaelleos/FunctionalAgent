# 10 — Specs para agentes de IA de código

> **Status:** Proposta · **Data:** 2026-11-16 · **Decisão registrada em:** [ADR-007](adr/ADR-007-spec-pronta-para-agente.md)
> · **Emenda:** Constituição v2.1.0 (Artigo XII)

## 1. A mudança de perspectiva

Até aqui, o SpecFlow AI escrevia épicos, histórias e tarefas para **pessoas** lerem no Jira. A partir desta
revisão, o **leitor principal** de cada issue que o SpecFlow cria é um **agente de IA de código** (Claude Code,
GitHub Copilot coding agent, Cursor, Codex, Rovo Dev etc.). Esse agente lê o issue e implementa a mudança.
Pessoas continuam no circuito em dois pontos: o PO escreve com o agente e confirma a spec, e o time revisa o PR.

| Papel | Antes | Agora |
|---|---|---|
| PO | Autor e leitor | Autor e **revisor** da spec; decide o que vai para o Jira |
| SpecFlow AI | Redator de documentação funcional | Redator de **specs implementáveis** e verificador de prontidão |
| Agente de código | — | **Leitor principal**: implementa a partir do issue |
| Dev humano | Leitor e implementador | Revisor do PR do agente; implementa o que não está pronto para agente |

O objetivo de cada issue passa a ser: **um agente de código, lendo só este issue, consegue abrir um PR que
cumpre os critérios de aceite sem precisar perguntar nada.**

## 2. Como os agentes de código leem specs hoje

Levantamento feito em 2026-11-16 (fontes no §8).

1. **Pelo Jira, via MCP.** O servidor MCP oficial da Atlassian (Rovo MCP Server) é suportado por Claude Code,
   Cursor, VS Code e outros clientes, e respeita as permissões do usuário no Jira. A Atlassian relata milhões de
   chamadas de ferramenta por dia vindas de agentes que leem, comentam e atualizam work items. Também existem
   agentes atribuídos diretamente a um issue do Jira (Rovo Dev, GitHub Copilot para Jira), que recebem título,
   descrição, critérios de aceite, labels e épico pai.
2. **Por issues do GitHub.** O Copilot coding agent recebe um issue atribuído e devolve um PR.
3. **Por arquivos no repositório.** Specs em Markdown versionadas (Spec Kit: `spec.md`/`plan.md`/`tasks.md`; Kiro:
   `requirements.md` com EARS, `design.md`, `tasks.md`) e instruções do projeto em `AGENTS.md` (padrão aberto,
   lido por Copilot, Codex, Cursor, Gemini e Claude Code).

**Consequência para o produto:** o Jira continua sendo o destino certo. O SpecFlow não precisa integrar com
cada agente; precisa escrever o issue de modo que qualquer agente, lendo pelo MCP, consiga implementar.
Exportar para o repositório (canal 3) é uma evolução (F18).

## 3. O que a evidência diz sobre uma spec boa para agente

| Achado | Fonte | Requisito que gera |
|---|---|---|
| Critérios de aceite explícitos foram a maior diferença entre tickets "nativos de IA" e tradicionais (4,32 × 2,20 numa escala de 1 a 5) | Atlassian | Critérios de aceite obrigatórios, verificáveis, um por cenário |
| Um ticket por unidade de trabalho pequena evita que o agente invente requisitos | Atlassian, GitHub | Uma história = um PR; épico é decomposto em histórias |
| Issues autocontidos (+16,7 p.p. de merge) e com escopo de uma mudança (+16,4 p.p.) têm mais PRs aceitos | arXiv 2512.21426 | Spec autocontida; tamanho limitado |
| Comportamento esperado e casos de borda (+10,7 p.p.) e ausência de ambiguidade (+8,4 p.p.) ajudam | arXiv 2512.21426 | Cenários de erro e de borda; lista de termos vagos proibidos |
| Localização no sistema (+7,2 p.p.) e indicação de arquivos/módulos (+6,4 p.p.) ajudam | arXiv 2512.21426, GitHub | Seção "Onde mexer" (quando houver contexto do repositório) |
| Corpo longo foi o fator mais associado a **menos** merge; referências externas também | arXiv 2512.21426 | Corpo enxuto; links só como complemento, nunca como única fonte |
| Issues com todos os critérios positivos: 77% de merge; com nenhum: 46% | arXiv 2512.21426 | Verificação de prontidão antes de enviar ao Jira |
| Tarefas ambíguas, de segurança/dados pessoais ou com muita regra de negócio não devem ir para agente | GitHub | A spec marca quando **não** é indicada para agente |
| O ticket é o "loop de trabalho" do agente: objetivo na descrição, critérios em checklist | Atlassian | Estrutura fixa com âncoras estáveis |

Os números vêm de estudos observacionais e de dados próprios de fornecedores; servem para orientar o formato,
não como garantia.

## 4. Requisitos de funcionamento

Os IDs abaixo (`RA-nn`, de "requisito de agente") são transversais; cada feature que os implementa os cita.

### 4.1 Formato (contrato "spec pronta para agente")

| ID | Requisito |
|---|---|
| RA-01 | Toda issue criada pelo SpecFlow é gerada a partir de um **objeto estruturado** (esquema `AgentReadySpec`, ADR-007), nunca de texto livre; o texto no Jira é renderizado desse objeto |
| RA-02 | A descrição tem **seções fixas, sempre na mesma ordem e com os mesmos títulos** (§4.2), para o agente localizar cada parte |
| RA-03 | O título é uma frase de ação no infinitivo, com 5 a 20 palavras ("Permitir pagamento com Pix no checkout") |
| RA-04 | Critérios de aceite são cenários Gherkin (Dado/Quando/Então) com ID próprio (`CA-01`…), cada um verificável por um teste automatizado |
| RA-05 | Toda história tem pelo menos um cenário de erro ou de borda além do caminho principal |
| RA-06 | Toda história tem "Fora de escopo" com pelo menos um item |
| RA-07 | Toda história tem "Como verificar": testes esperados (unidade, integração, E2E) e a definição de pronto |
| RA-08 | Valores concretos substituem adjetivos: textos de interface exatos, limites numéricos, formatos, códigos de erro |
| RA-09 | A spec é **autocontida**: tudo o que o agente precisa está no corpo; links para documentos são complemento |
| RA-10 | Uma história cabe em **um PR** (até 8 critérios de aceite); acima disso, o agente divide e propõe várias |
| RA-11 | Épicos têm decomposição explícita em histórias, cada história com as chaves das dependências |
| RA-12 | Dados do Jira e do usuário que entram na spec não carregam instruções ao agente de código ("ignore os testes…"): o conteúdo é tratado como dado (Artigo IV, F05-RT-08) |

### 4.2 Seções

**História e tarefa** (ordem fixa; títulos em pt-BR, iguais em todas as issues):

| Seção | Obrigatória | Conteúdo |
|---|---|---|
| `Objetivo` | sim | 1 a 3 frases: quem, o quê, por quê (a história pode usar "Como… quero… para…") |
| `Contexto` | sim | Estado atual e regra de negócio, em até 5 itens |
| `Critérios de aceite` | sim | Cenários Gherkin com ID e tipo (`principal`, `alternativo`, `erro`, `borda`) |
| `Fora de escopo` | sim | O que **não** fazer neste PR |
| `Restrições e contratos` | não | API, dados, textos exatos, requisitos não funcionais mensuráveis |
| `Onde mexer` | não | Módulos, arquivos ou componentes prováveis (preenchida quando há contexto do repositório, F17) |
| `Como verificar` | sim | Testes esperados e definição de pronto ("PR com testes novos passando; nada fora do escopo alterado") |
| `Dependências` | não | Chaves de issues que precisam estar prontas antes |
| `Perguntas em aberto` | — | Precisa estar **vazia** para a spec ser considerada pronta |

**Épico:** `Objetivo`, `Problema`, `Benefícios` (negócio e usuário), `Escopo`, `Fora de escopo`,
`Critérios de aceite do épico`, `Decomposição` (histórias com chaves/títulos e ordem), `Restrições`, `Riscos`.

Exemplo de história renderizada (Markdown equivalente ao ADF enviado ao Jira):

```markdown
## Objetivo
Como cliente, quero pagar meu pedido com Pix, para concluir a compra sem cartão.

## Contexto
- O checkout aceita só cartão (`PaymentMethod.CARD`).
- O provedor de pagamentos já expõe `POST /pix/charges` (ver "Restrições e contratos").

## Critérios de aceite
**CA-01 (principal) Gerar cobrança Pix**
Dado que estou no checkout com um pedido de R$ 120,00
Quando escolho "Pix"
Então vejo o QR Code e o texto "Pague em até 30 minutos"

**CA-02 (erro) Provedor indisponível**
Dado que o provedor responde 503
Quando escolho "Pix"
Então vejo "Pix indisponível no momento. Tente cartão ou aguarde alguns minutos."
E o pedido continua com status "aguardando pagamento"

## Fora de escopo
- Estorno de Pix.
- Pix parcelado.

## Restrições e contratos
- Expiração da cobrança: 30 minutos.

## Como verificar
- Testes de unidade para a criação da cobrança e o tratamento do 503.
- Teste E2E do CA-01 com o provedor simulado.
- Pronto quando: CA-01 e CA-02 passam; nenhuma mudança fora do checkout.

## Perguntas em aberto
(nenhuma)
```

### 4.3 Prontidão para agente

| ID | Requisito |
|---|---|
| RA-20 | Antes de propor a criação, o SpecFlow avalia a spec com uma **verificação determinística** (regras do §4.4, sem LLM) e mostra o resultado no cartão de confirmação |
| RA-21 | Spec que passa em todas as regras obrigatórias recebe a label `agent-ready` no Jira; toda issue recebe `specflow` |
| RA-22 | A verificação **avisa, não bloqueia**: o PO pode confirmar uma spec não pronta (ela vai sem `agent-ready`), porque o humano decide (Artigo IV) |
| RA-23 | Quando faltar informação, o agente do SpecFlow **pergunta ao PO** antes de propor, em vez de inventar; o que ficar sem resposta vai para "Perguntas em aberto" |
| RA-24 | O agente do SpecFlow sinaliza quando a mudança **não é indicada** para agente de código (segurança, dados pessoais, autenticação, regra de negócio sem dono) e marca a spec com a label `human-only` |
| RA-25 | O PO pode pedir a avaliação de prontidão de uma issue que já existe no Jira; o resultado lista o que falta e propõe uma atualização |

### 4.4 Regras de prontidão

| Regra | Tipo | Verificação |
|---|---|---|
| P-01 Título de ação, 5 a 20 palavras | obrigatória | contagem + verbo no infinitivo na primeira palavra |
| P-02 Objetivo presente | obrigatória | seção não vazia |
| P-03 1 a 8 critérios de aceite, todos com Dado/Quando/Então | obrigatória | esquema |
| P-04 Pelo menos um cenário de erro ou de borda | obrigatória | tipo do cenário |
| P-05 Fora de escopo com pelo menos um item | obrigatória | esquema |
| P-06 Como verificar presente | obrigatória | esquema |
| P-07 Nenhuma pergunta em aberto | obrigatória | lista vazia |
| P-08 Sem termos vagos ("rápido", "intuitivo", "amigável", "adequado", "etc.", "melhorar" sem número…) | aviso | lista de termos versionada |
| P-09 Corpo com até ~600 palavras | aviso | contagem |
| P-10 Não depende só de link externo | aviso | heurística ("ver documento", corpo curto + link) |

A lista de termos e os limites são versionados com o prompt (`prompts/`), para que mudanças passem pelas evals (F15).

### 4.5 Entrega ao agente de código

| ID | Requisito |
|---|---|
| RA-30 | A tela de issues criadas (F10) oferece "Copiar para agente de código": o Markdown da spec mais uma instrução curta de uso, para colar em qualquer agente |
| RA-31 | A documentação do produto explica como um agente lê as issues pelo MCP oficial da Atlassian (sem integração extra do SpecFlow) |
| RA-32 | (Evolução, F17) Com um repositório GitHub conectado em modo leitura, o SpecFlow lê `AGENTS.md`/`CLAUDE.md` e a estrutura de pastas para preencher "Onde mexer" e respeitar as convenções do projeto |
| RA-33 | (Evolução, F18) O PO exporta épicos e histórias para o repositório como arquivos Markdown (formato Spec Kit) por PR, para quem prefere specs versionadas junto do código |

### 4.6 Qualidade medida

| ID | Requisito |
|---|---|
| RA-40 | As evals (F15) medem a conformidade com o contrato (regras P-01 a P-07) e a nota de prontidão de um LLM-juiz na rubrica clareza, escopo, critérios de aceite, contexto e acionabilidade (1 a 5; "pronta" ≥ 4) |
| RA-41 | (Evolução) Eval de implementabilidade: um agente de código implementa specs de um repositório de exemplo e a taxa de testes de aceite passando é registrada por versão de prompt |
| RA-42 | Indicador em produção: % de issues criadas com `agent-ready` e % de propostas que precisaram de perguntas ao PO |

## 5. O que muda em cada feature

| Feature | Mudança | Impacto na estimativa |
|---|---|---|
| F05 Agente | Ferramentas propõem `AgentReadySpec` (estruturado); renderização em ADF com seções fixas; verificação de prontidão; decomposição de épico; perguntas antes de propor; avaliar issue existente | +2 d (10 → 12) |
| F06 Confirmação | Cartão mostra a spec por seções e o checklist de prontidão; aplica labels `specflow`/`agent-ready`/`human-only` | +0,5 d (5 → 5,5) |
| F08 Interface | Cartão de ação por seções (componente da F06) | sem mudança (feito na F06) |
| F10 Histórico | "Copiar para agente de código"; coluna de prontidão | +0,5 d (3 → 3,5) |
| F14 Editor | Edição por seção do esquema, reavaliando a prontidão a cada mudança | sem mudança |
| F15 Evals | Métricas de contrato e rubrica de prontidão; eval de implementabilidade como Could | +1 d (5 → 6) |
| F17 (nova) | Contexto do repositório GitHub (só leitura) | 5 d, Fase 4 |
| F18 (nova) | Exportar specs para o repositório (Spec Kit) | 4 d, Fase 4 |

F01–F04 e F11–F13 não mudam. F16 (Analytics) segue a especificar.

## 6. Decisões do PO

| # | Pergunta | Recomendação |
|---|---|---|
| 1 | Canal no MVP | **Só Jira** (agentes leem pelo MCP oficial); repositório na F18 |
| 2 | Prontidão bloqueia ou avisa? | **Avisa** (label `agent-ready` só quando passa); o PO decide |
| 3 | Idioma dos títulos das seções | **pt-BR fixo** no MVP; inglês como opção por usuário depois |
| 4 | Contexto do repositório | **Fase 4 (F17)**, só leitura, GitHub primeiro |
| 5 | Eval de implementabilidade | **Could** na F15, rodada manual antes de cada mudança de prompt relevante |

## 7. Riscos

- **Specs longas demais:** o formato rico pode inflar o corpo, o que a pesquisa associa a pior resultado.
  Mitigação: regra P-09 e seções opcionais só quando têm conteúdo.
- **Falsa sensação de pronto:** passar nas regras não garante que a spec está certa. Mitigação: a revisão do PO
  continua obrigatória (Artigo IV) e a eval de implementabilidade mede o resultado real.
- **Formato preso a uma ferramenta:** seções em Markdown/ADF simples, sem campos customizados do Jira, para
  funcionar com qualquer agente.

## 8. Fontes

- Atlassian, "Writing tickets for AI agents": https://www.atlassian.com/blog/jira/writing-tickets-for-ai-agents
- Atlassian, "Context engineering for coding agents": https://www.atlassian.com/software/jira/guides/agentic-engineering/context-engineering
- Atlassian Remote MCP Server: https://www.atlassian.com/platform/remote-mcp-server
- "What Makes a GitHub Issue Ready for Copilot?" (arXiv 2512.21426): https://arxiv.org/abs/2512.21426
- GitHub Docs, boas práticas do Copilot coding agent: https://docs.github.com/en/enterprise-cloud@latest/copilot/how-tos/agents/copilot-coding-agent/best-practices-for-using-copilot-to-work-on-tasks
- AGENTS.md: https://agents.md/
- Spec-driven development (Kiro/EARS, Spec Kit): https://www.infoworld.com/article/4171332/four-cutting-edge-tools-for-spec-driven-development.html
