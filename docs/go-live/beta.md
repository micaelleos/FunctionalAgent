# Beta com convidados (F12, 2026-11-19 → 2026-11-25)

**Objetivo:** pessoas de fora usam o app de verdade por uma semana, no próprio Jira, antes do go-live.
**Quem:** 3–5 POs/PMs convidados pelo PO. **Onde:** https://specsflow-ai.web.app (produção).
**Limites:** 20 mensagens e 200 mil tokens por pessoa por dia (renova às 00:00 de Brasília).

## Convite (para copiar)

> Oi! Estou testando o **SpecFlow AI**, um agente que transforma uma necessidade de produto em épicos,
> stories e tasks no Jira, escritos para um agente de código implementar. Topa usar por uns 20 minutos
> nesta semana e me contar o que achou?
>
> 1. Crie a conta em https://specsflow-ai.web.app (e-mail ou Google).
> 2. Em **Settings**, conecte o seu Jira: endereço do site, e-mail e um API token
>    (https://id.atlassian.com/manage-profile/security/api-tokens). Use um projeto de teste se preferir.
> 3. Siga o roteiro abaixo e me responda as perguntas.
>
> Nada é escrito no Jira sem você clicar em **Confirm**. Privacidade: https://specsflow-ai.web.app/privacy.
> Problemas: https://github.com/micaelleos/SpecFlowAI/issues ou direto comigo.

## Roteiro (≈ 20 min)

1. Em **Projects**, escolha um projeto e clique em **Chat about this project**.
2. Descreva uma necessidade real em poucas frases ("quero que o cliente receba um aviso quando…").
3. Responda às perguntas do agente até ele propor uma **story** (ou um **épico** com stories).
4. Leia o cartão da proposta. Ajuste pelo chat se algo estiver errado. Clique em **Confirm**.
5. Abra o issue no Jira pelo link do cartão e confira o texto.
6. Em **Issues**, veja o issue criado e copie a spec.
7. Opcional: peça para atualizar um campo de um issue existente e confirme.

## Perguntas de feedback

1. Conseguiu criar ao menos um issue? Se não, onde travou?
2. A story/épico ficou boa o bastante para um agente de código (ou um dev) implementar sem te perguntar nada?
3. O agente perguntou o que faltava ou inventou? Cite um exemplo.
4. Algo te deixou inseguro antes de clicar em **Confirm**?
5. O que você mais sentiu falta?
6. De 0 a 10, quanto recomendaria para outro PO?

## Acompanhamento (PO)

- Dashboard "specflow: operação" no Cloud Monitoring 1×/dia (não há alertas por e-mail).
- Teto do beta: 5 milhões de tokens do Gemini por mês para todos juntos; ao acabar, o chat avisa e
  volta no dia 1º (`docs/runbooks/limites-e-app-check.md`).
- Problema grave (perda de dado, escrita no Jira sem confirmação, vazamento): **Sev1** → rollback
  (`docs/runbooks/rollback.md`) e pausa do beta.
- Correções em PRs `fix/F12-*`.

## Resumo do feedback (preencher em 2026-11-25)

| Convidado (iniciais) | Criou issue? | Nota | Principais pontos |
|---|---|---|---|
