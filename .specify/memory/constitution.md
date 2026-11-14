# Constituição do Agente Funcional

**Missão:** ajudar Product Owners a transformar ideias em documentação funcional de qualidade
(épicos, user stories em BDD, tarefas) e a manter o backlog do Jira organizado — **com o humano
sempre no controle** do que é escrito em sistemas externos.

Os artigos abaixo são **inegociáveis**. Um artigo só pode ser violado com uma exceção registrada em
ADR (`docs/modernizacao/adr/`) e aprovada pelo dono do produto.

## Princípios Fundamentais

### I. Especificação antes do código

1. Nenhuma feature começa a ser implementada sem spec aprovada (Gate 0) contendo requisitos
   funcionais (RF), requisitos técnicos (RT) e um **teste final de aceitação** escrito antes da
   implementação.
2. Todo requisito tem um ID (`Fxx-RF-nn`, `Fxx-RT-nn`) e é rastreável até pelo menos um teste;
   `make trace` (`scripts/trace_requirements.py`) MUST passar no CI.
3. Mudanças de escopo durante a implementação MUST atualizar a spec no mesmo PR.

**Razão:** spec e teste de aceitação definem "pronto" antes do código, evitando retrabalho e escopo
implícito.

### II. Privacidade e isolamento por usuário

1. Todo dado de usuário é armazenado sob `users/{uid}/…` no Firestore e só é acessado pelo backend
   após verificar o ID token do Firebase daquele `uid`.
2. O cliente (navegador) MUST NOT acessar o Firestore diretamente; as regras de segurança negam tudo
   ao cliente.
3. Nenhum estado de usuário vive em memória global do processo (lição do problema D01).
4. O usuário MUST poder exportar e excluir todos os seus dados (LGPD, art. 18).
5. Logs MUST NOT conter tokens, senhas, conteúdo integral de mensagens ou PII além do `uid`.

**Razão:** o app legado vazava estado entre usuários; isolamento por `uid` verificado no servidor é
a única fronteira confiável.

### III. Segredos nunca em código nem no cliente

1. Segredos do sistema (chave do LLM etc.) ficam no **Secret Manager**, injetados no Cloud Run.
2. Credenciais de terceiros por usuário (tokens do Jira) são cifradas com **Cloud KMS** (envelope
   encryption) antes de gravar no Firestore e MUST NOT retornar ao frontend após salvas.
3. `gitleaks` roda em todo PR; um segredo detectado bloqueia o merge.

**Razão:** um vazamento de credencial do Jira expõe o backlog inteiro do cliente.

### IV. Humano no controle (INEGOCIÁVEL)

1. Toda ação do agente que **escreve** em sistema externo (criar, atualizar, mover, excluir no Jira)
   é apenas **proposta** e só é executada após confirmação explícita do usuário na interface.
2. A confirmação MUST ser aplicada **no código** (padrão "ação proposta", ADR-003), nunca apenas por
   instrução no prompt.
3. O payload executado MUST ser exatamente o payload que o usuário viu e confirmou.
4. Ferramentas de leitura podem ser executadas automaticamente, com limites de volume.

**Razão:** LLMs erram; o custo de uma escrita indevida no Jira recai sobre o usuário, não sobre o
agente.

### V. Contrato primeiro (API-first)

1. O contrato OpenAPI gerado pelo FastAPI é a fonte de verdade entre front e back.
2. O cliente TypeScript é **gerado** a partir do OpenAPI; o CI falha se estiver desatualizado.
3. Mudanças incompatíveis na API exigem nova versão de rota (`/api/v2/...`).

**Razão:** permite front e back em paralelo e elimina divergência silenciosa de tipos.

### VI. Testes como portão de qualidade

1. Nenhum merge com CI vermelho. Nenhum teste é desativado para "passar".
2. Cobertura mínima de linhas em código novo: **backend 80%**, **frontend 70%**.
3. Toda feature tem um **teste final de aceitação** automatizado (E2E ou integração) que mapeia cada
   RF.
4. Mudanças no prompt ou nas ferramentas do agente rodam a suíte de evals; regressão acima do limite
   bloqueia o merge.

### VII. Simplicidade serverless

1. Preferir serviços gerenciados que escalam a zero (Cloud Run, Firestore, Firebase Hosting).
2. Novo componente de infraestrutura (fila, cache, banco adicional) só com ADR justificando custo e
   necessidade.
3. Um backend, um frontend, um banco — até que um ADR prove o contrário.

**Razão:** projeto de equipe pequena; cada peça a mais é custo fixo e superfície operacional.

### VIII. Infraestrutura como código

1. Todo recurso de GCP/Firebase é declarado em Terraform (`infra/`). Nada é criado manualmente em
   `prd`.
2. Deploys acontecem apenas pelo pipeline, autenticado via Workload Identity Federation (sem chaves
   JSON).
3. Todo deploy MUST ser reversível em menos de 5 minutos (troca de tráfego entre revisões).

### IX. Observabilidade

1. Logs estruturados em JSON com `trace_id`, `uid` (pseudonimizado se necessário) e `request_id`.
2. Toda chamada ao LLM registra modelo, tokens de entrada/saída, latência e custo estimado.
3. Toda feature define pelo menos um indicador observável em produção (métrica, log ou alerta).

### X. Experiência do usuário e acessibilidade

1. Interface em **pt-BR** primeiro, com textos centralizados para futura internacionalização.
2. WCAG 2.1 AA: navegação por teclado, contraste, rótulos ARIA; `axe` roda nos testes E2E.
3. Resposta do agente em **streaming real** (primeiro token em ≤ 3 s no p75).
4. Erros são explicados em linguagem simples com ação sugerida ("Reconecte sua conta do Jira").

### XI. Qualidade do agente

1. Prompts são arquivos versionados (`system_vN.md`), nunca strings soltas no código.
2. Ferramentas do agente são funções puras de domínio, testáveis sem LLM e sem UI.
3. Toda user story gerada segue BDD (cenários + critérios de aceite); todo épico tem objetivo,
   benefício, escopo e critérios de aceite — verificados por evals.

## Restrições de Stack e Plataforma

- **Backend:** Python 3.12, uv (`uv.lock`), FastAPI + Pydantic v2, LangGraph para o agente, httpx
  para o Jira (API v3 com ADF). Qualidade: Ruff, mypy strict, import-linter.
- **Camadas do backend:** `api → services → agent | integrations | repositories → core`, verificadas
  pelo `import-linter`; importações no sentido inverso MUST falhar o lint.
- **Frontend:** React 19 + TypeScript strict, Vite, TanStack Query, Tailwind + shadcn/ui, cliente
  gerado com openapi-typescript. Testes: Vitest + Testing Library + MSW; Playwright + axe para E2E.
- **Plataforma:** Firebase Hosting, Firebase Auth + App Check, Cloud Run, Firestore (modo nativo),
  Secret Manager, Cloud KMS, Cloud Logging/Trace; Terraform com estado em GCS; GitHub Actions + WIF.
- **Monorepo** (ADR-005): `backend/`, `frontend/`, `infra/`, `scripts/`, `specs/` (features no formato
  Spec Kit, `Fxx` = pasta `0xx-slug`), `docs/modernizacao/` (plano, arquitetura, ADRs);
  `legacy/` (Streamlit) permanece só até o go-live (F12) e não recebe features novas.
- Trocar uma tecnologia listada acima exige ADR.

## Fluxo de Desenvolvimento e Gates

- **Ciclo:** Rascunho → Gate 0 (spec aprovada) → Gate 1 (plano aprovado) → Implementação →
  Gate 2 (merge) → Gate 3 (aceite em dev) → Gate 4 (verificação pós-deploy em ≤ 24 h).
- **Gate 0:** todo RF verificável e coberto por cenário de aceitação; fora de escopo explícito;
  seção "Conformidade com a Constituição" preenchida sem violações não justificadas.
- **Gate 1:** contrato de API definido antes do código; riscos e rollback descritos; tarefas ≤ 1 dia,
  cada uma com seu teste.
- **Gate 2:** CI verde (lint, tipos, testes, cobertura, contrato, segurança, evals se aplicável),
  review aprovado, spec atualizada se o escopo mudou. Branch `feat/Fxx-slug`, PRs pequenos
  (≤ 400 linhas idealmente), template de PR com checklist da Constituição.
- **Gate 3:** todos os cenários de aceitação passaram em dev; matriz RF → teste completa; PO aceitou.
- **Gate 4:** canário cumpriu SLOs; indicador do Artigo IX reportado; smoke de produção passou.
- Assistentes de IA podem redigir specs, planos e testes, mas **os gates continuam humanos**.

## Governança

- **Precedência:** em conflito, esta Constituição prevalece sobre specs, planos, ADRs e preferências
  de implementação.
- **Fonte única:** este arquivo (`.specify/memory/constitution.md`) e
  `docs/modernizacao/02-constituicao.md` MUST ter o mesmo conteúdo normativo e a mesma versão; uma
  emenda atualiza os dois no mesmo PR.
- **Emendas:** PR alterando a Constituição + ADR explicando o motivo; aprovação do dono do produto.
- **Versionamento:** SemVer — MAJOR remove ou redefine um artigo; MINOR adiciona artigo/seção ou
  amplia materialmente uma regra; PATCH esclarece texto sem mudar significado.
- **Conformidade:** toda spec tem a seção "Conformidade com a Constituição"; todo PR preenche o
  checklist correspondente; o revisor verifica os Artigos I–XI. Revisão da Constituição só por emenda,
  avaliada na retrospectiva de cada fase do roadmap.
- **Guia de execução:** `CONTRIBUTING.md`, `specs/ROADMAP.md` e
  `docs/modernizacao/08-processo-de-desenvolvimento.md`.

**Version**: 1.1.0 | **Ratified**: 2026-11-13 | **Last Amended**: 2026-11-14
