# ADR-004 — Credenciais do Jira: API token cifrado com KMS agora, OAuth 2.0 (3LO) depois

- **Status:** Aceito (implementado na F04) · **Data:** 2026-11-13 · **Revisado:** 2026-11-16

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

## Revisão de 2026-11-16 (plano da F04)

- **Cifra direta com `kms.encrypt`**, sem envelope: o token tem bem menos de 64 KiB e o custo do KMS é desprezível.
  O Firestore guarda `tokenCiphertext` e `kmsKeyVersion` (a versão da chave usada). Decisão do PO.
- O backend chama a API REST do KMS via `google-auth`, sem a biblioteca gRPC `google-cloud-kms`, que levava a
  imagem acima do limite de 300 MiB do CI.
- Em `local`/`test` a cifra é `LocalFernetCipher`; fora disso, sem `KMS_KEY_NAME`, a API não sobe (F04-RT-06).

