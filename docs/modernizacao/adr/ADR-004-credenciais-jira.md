# ADR-004 — Credenciais do Jira: API token cifrado com KMS agora, OAuth 2.0 (3LO) depois

- **Status:** Proposto · **Data:** 2026-11-13

## Contexto

Hoje o usuário digita URL, e-mail e API token do Jira num formulário; os valores ficam em texto puro na sessão
(D02). Precisamos armazenar a credencial de cada usuário para que o backend acesse o Jira em seu nome.

## Opções

| Opção | Segurança | Esforço | Experiência |
|---|---|---|---|
| A. API token cifrado (envelope KMS) no Firestore | Boa (token nunca sai do backend; decrypt só pela SA) | Baixo | Usuário precisa gerar o token manualmente |
| B. Um secret por usuário no Secret Manager | Boa | Médio; cobrança por secret ativo, cotas | Igual à A |
| C. OAuth 2.0 (3LO) Atlassian | Ótima (escopos, revogação, sem token manual) | Médio/alto (app no developer console, refresh tokens, `cloudid`) | Melhor: "Conectar com Atlassian" |

## Decisão

- **MVP (F04): opção A.** Envelope encryption: o backend gera uma DEK por credencial, cifra o token com AES-GCM,
  cifra a DEK com a chave KMS `jira-tokens` e grava `{ciphertext, wrappedDek, kmsKeyVersion}`. (Para simplificar,
  pode-se cifrar diretamente via `kms.encrypt`, já que o token tem < 64 KiB; a escolha final fica no plano da F04.)
- **Evolução (F13): opção C**, mantendo A como alternativa para Jira Data Center/servidores sem OAuth.

## Consequências

- ✅ Resolve D02 rapidamente, sem custo relevante.
- ✅ O modelo `jira_connections` já prevê `authType` para coexistir com OAuth.
- ⚠️ API token tem os mesmos poderes do usuário no Jira — por isso a confirmação humana (ADR-003) é obrigatória.
- ⚠️ Rotação da chave KMS a cada 90 dias: versões antigas continuam decifrando; job opcional re-cifra.
