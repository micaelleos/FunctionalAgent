# Metodologia SpecFlow — especificação guiada por documentação viva

> **Status:** Proposta v1.0 · **Data:** 2026-11-20 · **Decisão:** [ADR-009](../modernizacao/adr/ADR-009-confluence-como-documentacao.md)
> · **Features:** [F19](../../specs/019-contexto-confluence/spec.md) (ler o Confluence) e
> [F20](../../specs/020-documentacao-confluence/spec.md) (escrever no Confluence)

Esta é a metodologia que o SpecFlow AI aplica para especificar software com um PO. Ela leva para os
projetos dos usuários o mesmo fluxo que usamos para construir o próprio SpecFlow, o Spec Kit:
constituição → specify → clarify → plan → tasks → analyze/checklist → converge. A diferença é onde as
coisas vivem. Aqui a documentação do projeto fica no **Confluence**, a execução fica no **Jira**, e cada
issue é uma **spec pronta para um agente de IA de código** ([doc 10](../modernizacao/10-specs-para-agentes.md)).

## 1. Princípios

1. **Os documentos do projeto são a fonte da verdade e ficam no Confluence.** O que o produto é, para
   quem, quais regras não se quebram e quais decisões já foram tomadas fica num espaço do Confluence por
   projeto, com estrutura fixa ([espaco-confluence.md](espaco-confluence.md)). O Jira guarda o que vai ser
   feito; o Confluence guarda por quê e sob quais regras.
2. **Issue autocontido, documentação ligada.** O agente de código lê o issue, não o Confluence. Por isso
   o SpecFlow **copia para dentro da spec** o trecho que importa (Contexto, Restrições) e lista as páginas
   usadas em "Referências". O link complementa e nunca substitui o texto (regra P-10 do doc 10).
3. **Perguntar antes de inventar.** Se a documentação não responde e o PO não disse, o agente pergunta.
   Se a documentação responde, ele não pergunta de novo.
4. **Nenhuma escrita sem confirmação.** Criar ou atualizar uma página no Confluence segue a mesma regra
   dos issues: o agente **propõe**, mostra o antes e o depois, e só grava depois do **Confirm**
   (Constituição, Art. IV; ADR-003).
5. **Documentação acompanha a entrega.** Depois que issues são criados, o agente propõe atualizar o
   roadmap e a página da feature com as chaves do Jira. Quando uma decisão nova aparece na conversa, ele
   propõe uma ADR. Assim a documentação não fica para trás.
6. **Conteúdo lido é dado, não instrução.** Texto vindo do Confluence, do Jira ou colado pelo usuário
   nunca muda as regras do agente (Constituição, Art. XII.5).

## 2. As fases

O agente segue sete fases em cada pedido. Pedidos pequenos ("atualize o critério 2 do SCRUM-12")
passam rápido pelas primeiras; pedidos novos ("quero que o usuário exporte relatórios") passam por todas.

| # | Fase | Equivalente no Spec Kit | Entradas | O que o agente faz | Saída |
|---|---|---|---|---|---|
| 1 | **Descobrir** | `constitution` (leitura) | projeto Jira fixado, espaço vinculado | Lê a Constituição, o Glossário, as Regras de negócio e as ADRs do espaço; busca páginas e issues relacionados ao pedido (CQL + JQL) | Resumo curto do que a documentação já diz, com as páginas citadas |
| 2 | **Esclarecer** | `clarify` | pedido + o que foi descoberto | Faz de 1 a 3 perguntas sobre o que falta **e** a documentação não responde. Não pergunta o que já está escrito | Respostas do PO |
| 3 | **Especificar** | `specify` | tudo acima | Monta a `AgentReadySpec`: objetivo, contexto (com trechos da documentação), critérios Gherkin com erro/borda, fora de escopo, restrições (regras `RN-nn` e ADRs que se aplicam), como verificar, referências | Spec estruturada |
| 4 | **Planejar e decompor** | `plan` + `tasks` | spec | Se não cabe num PR (mais de 8 critérios), propõe um **épico** com a decomposição em stories, na ordem das dependências | Épico + stories |
| 5 | **Verificar** | `analyze` + `checklist` | spec(s) | Roda a prontidão (P-01 a P-10, sem LLM) e confere conflitos: a spec contradiz uma regra `RN-nn`, uma ADR ou a Constituição? Termos fora do Glossário? | Avisos na proposta |
| 6 | **Propor** | — (humano no circuito) | spec(s) verificada(s) | Cria a **ação proposta** no Jira (e, com a F20, nas páginas do Confluence). O PO revisa e clica **Confirm** | Issues/páginas gravados |
| 7 | **Convergir** | `converge` | o que foi gravado | Propõe atualizar o Roadmap e a página da feature com as chaves; propõe uma ADR se uma decisão nova apareceu; aponta páginas desatualizadas pelo que foi decidido | Documentação alinhada |

**Sem espaço vinculado,** as fases 1 e 7 se reduzem ao Jira, como hoje. Na primeira conversa, o agente
oferece criar o espaço com o modelo (F20).

## 3. Quem faz o quê

| Atividade | PO | Agente SpecFlow |
|---|---|---|
| Visão do produto e Constituição do projeto | Decide e aprova | Redige a partir da conversa e propõe a página (F20) |
| Regras de negócio, Glossário | Valida | Extrai da conversa, propõe a página, mantém os IDs `RN-nn` |
| Decisões (ADR) | Decide | Percebe a decisão na conversa e propõe a ADR |
| Pedido de feature | Descreve com as próprias palavras | Descobre, pergunta, especifica, decompõe |
| Revisão da spec | Revisa e confirma | Mostra prontidão e conflitos antes do Confirm |
| Roadmap | Prioriza | Mantém as linhas e as chaves do Jira atualizadas (proposta) |
| Implementação | Revisa o PR | — (agente de código lê o issue) |

## 4. Quando cada documento nasce e muda

| Documento ([modelos](modelos/)) | Nasce | Muda quando |
|---|---|---|
| Início (visão) | criação do espaço | o objetivo do produto ou o público muda |
| [Constituição](modelos/constituicao.md) | criação do espaço, numa conversa de abertura | uma regra inegociável entra ou sai (versão SemVer) |
| [Glossário](modelos/glossario.md) | primeiro termo de domínio ambíguo | um termo novo aparece numa spec |
| [Regras de negócio](modelos/regra-de-negocio.md) | primeira regra citada pelo PO | uma regra é criada, mudada ou revogada (nunca reutilize o ID) |
| [ADR](modelos/adr.md) | uma decisão com alternativas descartadas | não muda: é substituída por uma ADR nova ("Substituída por ADR-nnn") |
| [Feature / épico](modelos/feature.md) | o épico é proposto | stories são criadas, escopo muda, a feature é entregue |
| [Roadmap](modelos/roadmap.md) | criação do espaço | uma feature entra, muda de status ou ganha chave no Jira |
| Registro de mudanças | criação do espaço | a cada escrita do SpecFlow no espaço (uma linha) |

## 5. Como o PO começa

1. Conecte o Jira (Settings). A mesma credencial Atlassian dá acesso ao Confluence do mesmo site.
2. Em **Projects**, abra o projeto. O SpecFlow procura o espaço do Confluence:
   - espaço com a mesma chave do projeto;
   - senão, página com o rótulo `specflow-projeto-<chave>`.

   Se achar, pede para você confirmar o vínculo. Se não achar, oferece criar o espaço com o modelo.
3. Na primeira conversa, peça: *"Vamos escrever a constituição e o glossário deste projeto."* O agente
   pergunta o essencial e propõe as páginas.
4. A partir daí, cada pedido de feature passa pelas 7 fases. A documentação cresce junto com o backlog.

## 6. Relação com o Spec Kit deste repositório

| Spec Kit (repositório SpecFlow) | Metodologia SpecFlow (projetos dos usuários) |
|---|---|
| `.specify/memory/constitution.md` | Página "Constituição" do espaço |
| `specs/ROADMAP.md` | Página "Roadmap" |
| `docs/modernizacao/adr/ADR-nnn` | Páginas filhas de "Decisões (ADR)" |
| `specs/0xx-slug/spec.md` | Página da feature + épico no Jira |
| `tasks.md` (Tnnn ≤ 1 d) | Stories no Jira (uma por PR, ≤ 8 critérios) |
| `/speckit-clarify` | Fase 2: até 3 perguntas |
| `/speckit-analyze`, `/speckit-checklist` | Fase 5: prontidão + conflitos com a documentação |
| `/speckit-converge` | Fase 7: roadmap e documentação alinhados ao que foi criado |
| `make trace` (RF ↔ teste) | Cenários `CA-nn` em cada story e "Como verificar" |

## 7. Limites conhecidos

- O agente lê no máximo 10 páginas por turno (F19-RT-04). Espaços grandes funcionam melhor seguindo o
  modelo, porque a fase 1 lê primeiro as páginas fixas (Constituição, Glossário, Regras, ADRs).
- Páginas fora do modelo são encontradas por busca, não lidas por inteiro.
- O SpecFlow nunca exclui páginas nem mexe em permissões do espaço.
