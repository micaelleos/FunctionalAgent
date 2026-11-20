# ADR-009 — Confluence como documentação viva do projeto: leitura como contexto, escrita só por ação proposta

- **Status:** Aceito (pelo PO em 2026-11-20, após o aceite da F19) · **Data:** 2026-11-20
- **Requisitos:** [F19](../../../specs/019-contexto-confluence/spec.md), [F20](../../../specs/020-documentacao-confluence/spec.md)
  · **Metodologia:** [docs/metodologia](../../metodologia/README.md)
- **Relacionados:** ADR-003 (ações propostas), ADR-004 (credenciais), ADR-007 (spec pronta para agente)

## Contexto

O PO quer que a documentação principal de cada projeto viva no **Confluence**: visão, constituição,
glossário, regras de negócio, arquitetura, decisões e roadmap. Quer também que o agente do SpecFlow a
**leia** antes de escrever um issue e a **mantenha** alinhada com o que foi criado no Jira.

Hoje o agente só enxerga o Jira, e a documentação vive fora do fluxo. O prompt manda a spec ser
autocontida, e a regra P-10 avisa quando o issue depende de "ver confluence". O agente de código lê o
issue, não o Confluence.

## Opções

| Opção | Contexto para o agente | Esforço | Risco |
|---|---|---|---|
| A. PO cola trechos na conversa | Manual, incompleto | Nenhum | A documentação diverge do backlog |
| B. **Ler o Confluence do mesmo site Atlassian** (REST, credencial da F04) e escrever por ação proposta | Automático, por projeto | Médio | Injeção de prompt via página; escrita indevida |
| C. Indexar o espaço (embeddings, busca vetorial) | Melhor recuperação em espaços grandes | Alto (infra nova, Art. VII) | Cópia de dados do cliente; custo; desatualização |
| D. Rovo / MCP da Atlassian como fonte | Bom, mas fora do nosso controle | Médio | Depende de licença Rovo; difícil testar e limitar |

## Decisão

**Opção B**, em duas features:

1. **Credencial:** a mesma conexão Atlassian da F04 (site `https://<site>.atlassian.net`, e-mail, token
   cifrado por KMS). O Confluence Cloud responde em `/wiki` no mesmo host, então o guard de SSRF
   (`normalize_site_url`) continua valendo sem mudança. Token com escopo precisa dos escopos do
   Confluence. A F13 (OAuth) soma `read:page:confluence`, `read:space:confluence`, `search:confluence` e,
   para a F20, `write:page:confluence` e `write:space:confluence`.
2. **Vínculo a partir do projeto Jira**, descoberto automaticamente e salvo só depois do OK do usuário:
   - vínculo salvo;
   - espaço com a mesma chave;
   - página com o rótulo `specflow-projeto-<chave>`;
   - se nada for encontrado, proposta de criar o espaço com o modelo.

   O vínculo nativo "Project pages" do Jira não é usado: ele não tem API pública estável.
3. **Leitura (F19):**
   - ferramentas só de leitura, restritas ao espaço vinculado: busca CQL, página, árvore do modelo;
   - conteúdo convertido para Markdown, com limite de tamanho, e marcado como **não confiável**
     (`<dados_confluence confiavel="nao">`), como já fazemos com o Jira;
   - nada é guardado além do vínculo;
   - o agente **copia para a spec** o que importa e lista as páginas numa seção nova, "Referências"
     (`references` na `AgentReadySpec`). A spec continua autocontida e a P-10 continua valendo.
4. **Escrita (F20):**
   - criar o espaço, criar páginas e atualizar páginas, sempre como **ação proposta** (ADR-003), com
     diff antes/depois e o mesmo hash entre o que foi confirmado e o que foi executado;
   - a atualização envia a versão vista (`version.number + 1`); se a página mudou depois da proposta,
     o Confluence recusa (409), a ação falha sem sobrescrever, e o agente relê a página e propõe de novo;
   - sem exclusão de páginas e sem mudança de permissões;
   - auditoria `confluence_write` nos logs, sem conteúdo.
5. **Metodologia:** as fases Descobrir → Esclarecer → Especificar → Planejar → Verificar → Propor →
   Convergir ficam no prompt versionado (`system_v2.md`). O formato do espaço e os modelos de página
   ficam em `docs/metodologia/`.

## Consequências

- **Positivas:**
  - issues com contexto real do projeto: regras `RN-nn` e ADRs entram em "Restrições";
  - a documentação acompanha o backlog;
  - nenhuma infraestrutura nova.
- **Negativas:**
  - mais chamadas por turno, com latência (limites na F19-RT-04);
  - espaços fora do modelo rendem menos;
  - a `AgentReadySpec` muda (`references`), o que exige uma versão nova do esquema e evals.
- **Riscos e mitigação:**
  - injeção de prompt via página → conteúdo marcado como não confiável, regra no prompt e evals de
    injeção;
  - escrita indevida → ação proposta com controle de versão;
  - vazamento entre usuários → leitura sempre com a credencial do próprio usuário (as permissões do
    Confluence valem como estão).
- **Constituição:** o Art. IV já cobre qualquer escrita externa. O Art. XII.5 ("conteúdo vindo do Jira
  ou do usuário") passa a citar o Confluence no PR de implementação da F19 (PATCH, nos dois espelhos).
