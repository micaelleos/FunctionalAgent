# F04 — Conexão Jira por usuário — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- **API** (`/api/v1/jira/connections`, todas exigem login):
  - `GET` → `[{id, site_url, email, account_name, token_hint, status, last_validated_at}]` (`status`: `ok` | `invalid`).
  - `POST {site_url, email, api_token}` → valida no Jira e cria (201). Já existe uma → 409 `jira-connection-exists`.
  - `PUT /{id} {site_url, email, api_token}` → valida e substitui a credencial.
  - `POST /{id}/validate` → testa a credencial guardada; 401 do Jira marca `invalid` e responde a conexão.
  - `DELETE /{id}` → 204 (idempotente).
  - Erros (Problem Details, F03-RT-05): `jira-invalid-url` (422), `jira-invalid-credentials` (422),
    `jira-unreachable` (502), `jira-connection-not-found` (404). O `id` da rota só é procurado em
    `users/{uid do token}` (F03-RT-02): o de outro usuário dá 404. Campos em snake_case, como `/api/v1/me`;
    o documento no Firestore usa camelCase.
- **Cifra (ADR-004, decidido aqui):** `kms.encrypt` direto com a chave `jira-tokens` (token < 64 KiB). O documento
  guarda `tokenCiphertext` (bytes) e `kmsKeyVersion`. `core/crypto.py`: protocolo `Cipher`, `KmsCipher`
  (API REST do KMS via `google-auth`; a biblioteca gRPC `google-cloud-kms` levava a imagem a 300,4 MiB,
  acima do limite de 300 MiB do CI) e `LocalFernetCipher` (`ENV` `local`/`test`, chave de `LOCAL_CIPHER_KEY` ou fixa de dev).
- **Back:**
  - `integrations/jira/urls.py` (`normalize_site_url`), `integrations/jira/client.py` (`JiraClient` async, Basic auth,
    `myself()`, retries/timeouts, `follow_redirects=False`; erros `JiraAuthError`, `JiraUnreachableError`).
  - `repositories/jira_connections.py` (`users/{uid}/jira_connections/{id}`).
  - `services/jira_connections.py` (`JiraConnectionService`: listar, criar, substituir, validar, remover;
    `client_for(uid)` decifra o token por requisição e é a fábrica que F05/F09/F10 usam).
  - `api/v1/jira.py`; `UserRepository.export` omite `tokenCiphertext`.
  - Documento: `{siteUrl, email, accountId, accountName, tokenHint, tokenCiphertext, kmsKeyVersion, authType:
    "api_token", status, createdAt, lastValidatedAt}`.
- **Front:**
  - `product/http.ts`: `createHttpProductApi(getToken)` substitui os métodos de conexão de `unavailableProductApi`
    (`features.jira = true`); `App` passa a usá-lo por padrão.
  - `SettingsPage`: "Conectado como …", "Testar conexão", "Trocar credencial" (site e e-mail preenchidos),
    estado inválido com "Reconectar".
  - `AppLayout`: aviso global "Sua conexão com o Jira expirou" quando `status = invalid`.
  - `ProjectsPage`: com o Jira conectado e sem a F09, diz que a lista de projetos chega na próxima versão
    (`features.projects = false`), em vez de "0 projetos".
- **Infra:** nada novo. Chave `jira-tokens`, papel `cryptoKeyEncrypterDecrypter` da SA de runtime e
  `KMS_KEY_NAME` no Cloud Run já existem (F02).
- **Rollback:** revisão anterior; dados aditivos (subcoleção nova).

### 9. Plano de testes
- Unit (respx): URL, retries/`Retry-After`, timeouts, mapeamento 401/403/404/erro de rede, cifra local.
- Integração (emuladores): rotas com Jira simulado, doc cru sem token em claro, isolamento entre usuários,
  exportação sem ciphertext.
- Redação de logs: injeta token conhecido, executa o fluxo com `caplog` em DEBUG → zero ocorrências.
- Vitest + MSW: tela de configurações (conectar, erros, trocar, remover, inválida) e aviso global.
- Playwright contra `make dev` + Jira sandbox (AT-F04-01/02/03/05); roteiro manual M-F04-01 em produção com
  token revogado (AT-F04-04).
