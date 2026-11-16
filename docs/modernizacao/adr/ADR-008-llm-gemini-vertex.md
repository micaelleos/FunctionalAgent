# ADR-008 — LLM do agente: Gemini no Vertex AI, com o SDK `google-genai` e loop próprio

- **Status:** Aceito pelo PO em 2026-11-16 · **Data:** 2026-11-16
- **Substitui:** a parte de ADR-003 que escolhia LangGraph e o provedor (OpenAI). O padrão "ação proposta" e o
  agente sem estado no processo continuam valendo.
- **Emenda:** Constituição v2.2.0 (Restrições de Stack e Plataforma; Artigo III.1)

## Contexto

A F05 vai construir o agente de chat. O plano anterior (ADR-003) usava LangGraph com `init_chat_model` e OpenAI,
herança do protótipo em LangChain. O PO decidiu, em 2026-11-16, trocar de provedor e "ir no mais simples".

Requisitos que o loop do agente precisa atender (F05, ADR-003, ADR-007):

- streaming de texto e de eventos de ferramenta para o SSE (`03-arquitetura.md §3.5`);
- ferramentas próprias, com o cliente Jira do usuário injetado por requisição e nenhuma ferramenta de escrita
  executando no Jira (só ações propostas);
- no máximo 8 iterações por turno, histórico carregado do Firestore a cada turno (nada em memória global);
- imagem do backend abaixo de 300 MiB (F01-RT-05; hoje em 293,5 MiB) e o Cloud Run atual (1 vCPU, 1 GiB, até 40
  requisições simultâneas);
- dados dos usuários não usados para treinar modelos (Artigo II).

## Opções consideradas

1. **LangGraph + OpenAI** (plano anterior). Funciona, mas traz LangChain/LangGraph inteiros (dependências pesadas
   para uma imagem já perto do limite) e camadas de abstração que o loop do SpecFlow não usa.
2. **Claude Agent SDK** (Anthropic). Avaliado em 2026-11-16: o pacote traz o CLI do Claude Code embutido
   (binário de 349 MiB descompactado, medido no wheel `claude-agent-sdk 0.2.182`), roda um subprocesso por
   conversa (a documentação recomenda ~1 GiB de RAM por sessão) e guarda as conversas em disco local, exigindo um
   `SessionStore` próprio. Exigiria emendar o limite da imagem e redimensionar o Cloud Run. Recusado pelo PO.
3. **SDK `anthropic` + Tool Runner.** Leve e adequado, mas o PO preferiu ficar no ecossistema Google.
4. **Gemini via SDK `google-genai`, com loop próprio** — escolhida.

Para o acesso ao Gemini, duas variantes:

- **Gemini API com chave** (Google AI Studio): chave no Secret Manager; precisa ser do nível pago, porque no
  gratuito o Google usa os dados para melhorar produtos.
- **Vertex AI** — escolhida: autenticação pela conta de serviço do Cloud Run (sem chave para guardar), no mesmo
  projeto GCP, dados não usados para treino.

## Decisão

- **Provedor:** Gemini no **Vertex AI**, no projeto `pcb-inspect`, autenticado pela SA de runtime do
  `specflow-api` (ADC). Não há chave de LLM.
- **SDK:** `google-genai` (oficial do Google), cliente criado com `vertexai=True`, `project` e `location`.
- **Modelo padrão:** `gemini-3.5-flash-lite` (escolha do PO por custo: US$ 0,30 / 2,50 por milhão de tokens de
  entrada/saída na tabela pública de 2026-11-16). Configurável por `LLM_MODEL`, sem mudar código; alternativas
  avaliadas: `gemini-4-hydrogen` e `gemini-3.8-flash` (US$ 1,50 / 7,50 a partir de 2027).
- **Loop próprio**, em `app/agent/loop.py`, em vez de LangGraph:
  - chamada em streaming ao modelo com as declarações de ferramentas;
  - para cada chamada de função: valida a entrada com Pydantic, executa a ferramenta com o `ToolContext` da
    requisição (uid, cliente Jira, conversa, repositórios) e devolve o resultado ao modelo;
  - para quando o modelo responde sem chamar ferramenta ou ao atingir 8 iterações;
  - emite os eventos SSE (`token`, `tool_start`, `tool_end`, `action_proposed`, `done`, `error`).
  - A chamada ao modelo fica atrás de uma interface pequena (`ModelClient`), que os testes substituem por um
    modelo roteirizado; trocar de provedor no futuro é trocar essa implementação.
- **Infraestrutura (na F05, via Terraform, com aprovação do PO):** ativar a API `aiplatform.googleapis.com` no
  projeto e dar `roles/aiplatform.user` à SA `specflow-api`; variáveis `LLM_MODEL` e `LLM_LOCATION` no Cloud Run.
  O segredo vazio `specflow-llm-api-key` (F02) deixa de ser necessário e é removido.

## Consequências

- ✅ Sem segredo de LLM para guardar, girar ou vazar (Artigo III fica mais simples).
- ✅ Dependência pequena: cabe no limite de 300 MiB da imagem e na configuração atual do Cloud Run.
- ✅ Loop de ~100 linhas, totalmente testável com modelo roteirizado; o padrão "ação proposta" não muda.
- ✅ Dados processados no Vertex AI não são usados para treinar modelos (Artigo II).
- ⚠️ O modelo padrão é o mais barato da linha e pode errar mais em specs longas, decomposição de épicos e
  perguntas de esclarecimento. Mitigação: as evals da F05/F15 medem o contrato do ADR-007; se a qualidade não
  atingir o limite, trocar `LLM_MODEL` (decisão de custo do PO).
- ⚠️ Ativar uma API e dar um papel IAM mexem no projeto compartilhado. É uma ativação aditiva, restrita à SA do
  specflow, e não altera configurações de outros apps (F02-RT-09), mas exige a aprovação explícita do PO no
  `terraform apply`.
- ⚠️ Nomes e disponibilidade de modelos no Vertex AI podem diferir do Google AI Studio e mudam com frequência
  (ex.: o `gemini-2.5-flash` será redirecionado em 2026-12-01). A tarefa da F05 confirma o ID no Vertex antes de
  fixar o padrão, e o smoke de deploy chama o modelo configurado.
- ⚠️ Sem LangGraph, recursos como checkpointer e grafos complexos não estão disponíveis; o SpecFlow não os usa
  (ADR-003 já descartou `interrupt()` + checkpointer).

## Fontes

- Modelos Gemini e descontinuações: https://aistudio.google.com/docs/models (consultado em 2026-11-16)
- Preços: https://aistudio.google.com/docs/pricing (consultado em 2026-11-16)
- Claude Agent SDK, hospedagem e sessões: https://code.claude.com/docs/en/agent-sdk/hosting e
  https://code.claude.com/docs/en/agent-sdk/session-storage (consultados em 2026-11-16)
