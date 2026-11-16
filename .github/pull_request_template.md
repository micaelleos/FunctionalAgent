## Feature e requisitos

- Feature: `Fxx` — <link para specs/0xx-slug/spec.md>
- Requisitos atendidos neste PR: `Fxx-RF-nn`, `Fxx-RT-nn`

## O que muda

<!-- Resumo curto da mudança e da abordagem -->

## Checklist da Constituição

- [ ] **I** — Spec aprovada; spec atualizada se o escopo mudou
- [ ] **II** — Dados sob `users/{uid}`; `uid` vem do token; nada de estado global de usuário
- [ ] **III** — Nenhum segredo em código, logs ou respostas da API
- [ ] **IV** — Nenhuma escrita em sistema externo sem ação proposta + confirmação
- [ ] **V** — Contrato OpenAPI e cliente TS atualizados (se a API mudou)
- [ ] **VI** — Testes novos marcados com os IDs dos requisitos; cobertura mantida
- [ ] **VIII** — Mudanças de infra feitas em Terraform
- [ ] **IX** — Logs/métricas para o comportamento novo
- [ ] **X** — Textos em pt-BR, acessibilidade verificada (se houver UI)
- [ ] **XI** — Evals rodadas (se mudou prompt, modelo ou ferramentas)
- [ ] **XII** — Specs geradas seguem o `AgentReadySpec` e a verificação de prontidão (se mudou o formato das issues)

## Evidências de teste

<!-- Saída de testes relevantes, screenshots, link da execução do CI / preview -->

## Rollback

<!-- Como desfazer esta mudança se der problema -->
