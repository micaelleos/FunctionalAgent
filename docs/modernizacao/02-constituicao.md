# 02 — Constituição do Agente Funcional

> A Constituição define os princípios **inegociáveis** do projeto. Toda spec de feature tem uma seção
> "Conformidade com a Constituição" e todo PR tem o checklist correspondente. Um artigo só pode ser
> violado com uma exceção registrada em ADR e aprovada pelo dono do produto.

**Versão:** 1.0.0 · **Ratificada em:** 2026-11-13 (proposta)

---

## Missão

Ajudar Product Owners a transformar ideias em documentação funcional de qualidade (épicos, user stories em
BDD, tarefas) e a manter o backlog do Jira organizado — **com o humano sempre no controle** do que é escrito
em sistemas externos.

---

## Artigo I — Especificação antes do código

1. Nenhuma feature começa a ser implementada sem uma spec aprovada (Gate 0) contendo requisitos funcionais
   (RF), requisitos técnicos (RT) e um **teste final de aceitação** escrito antes da implementação.
2. Todo requisito tem um ID (`Fxx-RF-nn`, `Fxx-RT-nn`) e é rastreável até pelo menos um teste.
3. Mudanças de escopo durante a implementação atualizam a spec no mesmo PR.

## Artigo II — Privacidade e isolamento por usuário

1. Todo dado de usuário é armazenado sob o caminho `users/{uid}/…` no Firestore e só é acessado pelo backend
   após verificar o ID token do Firebase daquele `uid`.
2. O cliente (navegador) **não** acessa o Firestore diretamente; as regras de segurança negam tudo ao cliente.
3. Nenhum estado de usuário vive em memória global do processo (lição do problema D01).
4. O usuário pode exportar e excluir todos os seus dados (LGPD, art. 18).
5. Logs nunca contêm tokens, senhas, conteúdo integral de mensagens ou PII além do `uid`.

## Artigo III — Segredos nunca em código nem no cliente

1. Segredos do sistema (chave do LLM etc.) ficam no **Secret Manager**, injetados no Cloud Run.
2. Credenciais de terceiros por usuário (tokens do Jira) são cifradas com **Cloud KMS** (envelope encryption)
   antes de gravar no Firestore e **nunca** retornam ao frontend após salvas.
3. `gitleaks` roda em todo PR; um segredo detectado bloqueia o merge.

## Artigo IV — Humano no controle

1. Toda ação do agente que **escreve** em sistema externo (criar, atualizar, mover, excluir no Jira) é
   apenas **proposta** pelo agente e só é executada após confirmação explícita do usuário na interface.
2. A confirmação é aplicada **no código** (padrão "ação proposta", ver ADR-003), nunca apenas por instrução
   no prompt.
3. O payload executado é exatamente o payload que o usuário viu e confirmou.
4. Ferramentas de leitura podem ser executadas automaticamente, com limites de volume.

## Artigo V — Contrato primeiro (API-first)

1. O contrato OpenAPI gerado pelo FastAPI é a fonte de verdade entre front e back.
2. O cliente TypeScript é **gerado** a partir do OpenAPI; o CI falha se o cliente estiver desatualizado.
3. Mudanças incompatíveis na API exigem nova versão de rota (`/api/v2/...`).

## Artigo VI — Testes como portão de qualidade

1. Nenhum merge com CI vermelho. Nenhum teste é desativado para "passar".
2. Cobertura mínima de linhas: **backend 80%**, **frontend 70%** (em código novo).
3. Toda feature tem um **teste final de aceitação** automatizado (E2E ou integração) que mapeia cada RF.
4. Mudanças no prompt ou nas ferramentas do agente rodam a suíte de evals; regressão acima do limite bloqueia.

## Artigo VII — Simplicidade serverless

1. Preferir serviços gerenciados que escalam a zero (Cloud Run, Firestore, Firebase Hosting).
2. Novo componente de infraestrutura (fila, cache, banco adicional) só com ADR justificando custo e necessidade.
3. Um backend, um frontend, um banco — até que um ADR prove o contrário.

## Artigo VIII — Infraestrutura como código

1. Todo recurso de GCP/Firebase é declarado em Terraform (`infra/`). Nada é criado manualmente em `prd`.
2. Deploys acontecem apenas pelo pipeline, autenticado via Workload Identity Federation (sem chaves JSON).
3. Todo deploy é reversível em menos de 5 minutos (troca de tráfego entre revisões).

## Artigo IX — Observabilidade

1. Logs estruturados em JSON com `trace_id`, `uid` (pseudonimizado se necessário) e `request_id`.
2. Toda chamada ao LLM registra modelo, tokens de entrada/saída, latência e custo estimado.
3. Toda feature define pelo menos um indicador observável em produção (métrica, log ou alerta).

## Artigo X — Experiência do usuário e acessibilidade

1. Interface em **pt-BR** primeiro, com textos centralizados para futura internacionalização.
2. WCAG 2.1 AA: navegação por teclado, contraste, rótulos ARIA; `axe` roda nos testes E2E.
3. Resposta do agente em **streaming real** (primeiro token em ≤ 3 s no p75).
4. Erros são explicados em linguagem simples com ação sugerida ("Reconecte sua conta do Jira").

## Artigo XI — Qualidade do agente

1. Prompts são arquivos versionados (`system_vN.md`), nunca strings soltas no código.
2. Ferramentas do agente são funções puras de domínio, testáveis sem LLM e sem UI.
3. Toda user story gerada segue BDD (cenários + critérios de aceite); todo épico tem objetivo, benefício,
   escopo e critérios de aceite — verificados por evals.

---

## Governança

- **Emendas:** PR alterando este arquivo + ADR explicando o motivo; aprovação do dono do produto.
- **Versionamento:** SemVer — MAJOR remove/redefine um artigo, MINOR adiciona artigo, PATCH esclarece texto.
- **Precedência:** em conflito, a Constituição prevalece sobre specs, planos e preferências de implementação.
