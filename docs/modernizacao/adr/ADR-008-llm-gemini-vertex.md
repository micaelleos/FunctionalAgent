# ADR-008 — LLM do agente: Gemini no Vertex AI, mantendo LangGraph

- **Status:** Aceito pelo PO em 2026-11-16 · **Data:** 2026-11-16
- **Altera:** ADR-003 só no provedor (OpenAI → Gemini no Vertex AI). LangGraph, o agente sem estado no processo e o
  padrão "ação proposta" continuam valendo.
- **Emendas:** Constituição v2.2.0 (Restrições de Stack e Plataforma; Artigo III.1) e F01-RT-05 (imagem do backend
  < 400 MiB, antes < 300 MiB)

## Contexto

O ADR-003 escolheu LangGraph com o modelo instanciado por configuração e OpenAI como provedor, herança do protótipo.
Ao começar a F05, o PO decidiu em 2026-11-16 trocar o provedor para Gemini e manter o LangGraph.

Restrições que pesaram:

- imagem do backend em 293,5 MiB, com limite de 300 MiB no CI (F01-RT-05);
- dados dos usuários não podem ser usados para treinar modelos (Artigo II);
- segredos do sistema no Secret Manager (Artigo III), de preferência nenhum.

## Opções consideradas

### Framework do agente

1. **LangGraph (mantido)**, com `langchain-google-genai`. Troca de provedor por configuração; ciclo
   modelo ⇄ ferramentas e streaming de eventos prontos. Acrescenta ~52 MiB de pacotes Python (medido em
   2026-11-16: `langgraph 1.2.22`, `langchain-core 1.8.1`, `langchain-google-genai 4.5.0`, `langsmith`).
2. Loop próprio sobre o SDK `google-genai`. Acrescenta ~10 MiB, mas cada troca de provedor exige um cliente novo.
   Também passaria do limite de 300 MiB (~304 MiB estimados).
3. Claude Agent SDK. Traz o CLI do Claude Code embutido (349 MiB descompactados no wheel
   `claude-agent-sdk 0.2.182`), roda um subprocesso por conversa (~1 GiB de RAM por sessão, pela documentação) e
   guarda as conversas em disco local. Recusado pelo PO.

O provedor mudou três vezes no mesmo dia (OpenAI, Claude, Gemini). Manter a troca por configuração vale os ~42 MiB
a mais em relação ao loop próprio.

### Acesso ao Gemini

- Gemini API com chave (Google AI Studio): exige guardar a chave e usar o nível pago (no gratuito o Google usa os
  dados para melhorar produtos).
- **Vertex AI (escolhido):** autenticação pela conta de serviço do Cloud Run, sem chave; dados não usados para
  treino; mesmo projeto GCP.

## Decisão

- **LangGraph** continua sendo o loop do agente (ADR-003).
- **Modelo de chat:** `ChatGoogleGenerativeAI` (`langchain-google-genai`, sobre o SDK oficial `google-genai`) com
  `vertexai=True`, `project` e `location`, criado por uma fábrica em `app/agent/` a partir de `LLM_PROVIDER`
  (`google_vertexai`) e `LLM_MODEL`. Trocar de provedor é acrescentar um ramo à fábrica e o pacote LangChain dele.
- **Modelo padrão:** `gemini-3.5-flash-lite` (escolha do PO por custo: US$ 0,30 / 2,50 por milhão de tokens de
  entrada/saída na tabela pública de 2026-11-16). Configurável por `LLM_MODEL` sem mudar código.
- **Autenticação:** conta de serviço `specflow-api` (ADC). Não há chave de LLM.
- **Imagem:** limite da F01-RT-05 sobe de 300 MiB para **400 MiB**. Com LangGraph a imagem deve ficar em ~345 MiB.
- **Infraestrutura (na F05, via Terraform, com aprovação do PO no apply):** ativar `aiplatform.googleapis.com`
  no projeto e dar `roles/aiplatform.user` à SA `specflow-api`; variáveis `LLM_PROVIDER`, `LLM_MODEL` e
  `LLM_LOCATION` no Cloud Run. O segredo vazio `specflow-llm-api-key` (F02) deixa de ser necessário e é removido.

## Consequências

- ✅ Plano da F05 quase intacto: grafo, ferramentas, `RunnableConfig` e "ação proposta" seguem o ADR-003.
- ✅ Sem segredo de LLM para guardar, girar ou vazar.
- ✅ Dados processados no Vertex AI não são usados para treinar modelos (Artigo II).
- ✅ Trocar de provedor ou de modelo continua sendo configuração.
- ⚠️ Imagem ~50 MiB maior, cold start um pouco mais lento. O CI passa a aceitar até 400 MiB.
- ⚠️ O modelo padrão é o mais barato da linha e pode errar mais em specs longas, decomposição de épicos e
  perguntas de esclarecimento. As evals da F05/F15 medem o contrato do ADR-007; se a qualidade não bastar, trocar
  `LLM_MODEL` (decisão de custo do PO; alternativas: `gemini-4-hydrogen`, `gemini-3.8-flash`).
- ⚠️ Ativar uma API e dar um papel IAM mexem no projeto compartilhado. A ativação é aditiva e o papel fica restrito
  à SA do specflow (F02-RT-09), mas exige a aprovação explícita do PO no `terraform apply`.
- ⚠️ IDs e disponibilidade de modelos no Vertex AI podem diferir do Google AI Studio e mudam com frequência. A
  tarefa T010 da F05 confirma o ID antes de fixar o padrão, e o smoke do deploy chama o modelo configurado.

## Fontes

- Modelos Gemini e descontinuações: https://aistudio.google.com/docs/models (consultado em 2026-11-16)
- Preços: https://aistudio.google.com/docs/pricing (consultado em 2026-11-16)
- Claude Agent SDK, hospedagem e sessões: https://code.claude.com/docs/en/agent-sdk/hosting e
  https://code.claude.com/docs/en/agent-sdk/session-storage (consultados em 2026-11-16)
- Tamanhos medidos com `uv pip install` sobre as dependências de runtime do backend (`uv export --no-dev`).
