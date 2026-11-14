# ADR-002 — Firebase Hosting para o SPA e Cloud Run para a API, com chamada direta

- **Status:** Proposto · **Data:** 2026-11-13

## Contexto

O frontend React é um SPA estático; o backend Python precisa de processo de longa duração para streaming do
agente (turnos de 10–120 s com várias ferramentas). Opções de hospedagem do backend: Cloud Run, Cloud Functions
(2ª geração — que roda sobre Cloud Run), App Engine, GKE. Para o roteamento entre front e back:

1. **Rewrite do Firebase Hosting** `/api/** → Cloud Run` (mesma origem).
2. **Chamada direta** do SPA à URL do Cloud Run (`api.<domínio>` ou `*.run.app`) com CORS.
3. **Load Balancer HTTPS** global na frente de ambos.

## Decisão

- **Frontend:** Firebase Hosting (CDN, HTTPS, previews por PR, integração com Firebase Auth).
- **Backend:** **Cloud Run** (container, FastAPI) — controle total do runtime, streaming, timeout até 60 min,
  divisão de tráfego entre revisões para canário/rollback, escala a zero.
- **Roteamento:** **opção 2 — chamada direta**, com `Authorization: Bearer <ID token>` e CORS restrito à origem
  do Hosting.

## Motivos

- O rewrite do Hosting para Cloud Run tem **limite de 60 s por requisição**, incompatível com turnos longos do
  agente em streaming; misturar (rewrite para rotas curtas, direto para o chat) traria duas formas de acesso.
- Autenticação por header (não cookie) elimina riscos de CSRF e simplifica CORS.
- O Load Balancer resolveria tudo na mesma origem, mas custa ~US$ 18+/mês fixo e adiciona componentes
  (Artigo VII). Fica como evolução se precisarmos de Cloud Armor/WAF.
- Cloud Functions não oferece vantagem sobre Cloud Run para uma API FastAPI completa; App Engine/GKE são mais caros/complexos.

## Consequências

- ✅ Sem limite de 60 s; streaming SSE nativo.
- ✅ Rollback por revisão em segundos.
- ⚠️ CORS precisa listar as origens de cada ambiente. Sem previews (ADR-006), basta a lista fixa do site
  (`specsflow-ai.web.app` e `.firebaseapp.com`).
- ⚠️ Proteção contra abuso fica na aplicação (App Check + cotas) em vez de WAF — revisar se houver ataques.
- 🔧 Verificar, no momento da F02, se os limites do rewrite do Hosting mudaram; a decisão pode ser simplificada se sim.
