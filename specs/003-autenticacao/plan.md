# F03 — Autenticação e conta do usuário — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- **Back** (camadas `api → services → repositories → core`):
  - `core/auth.py`: verificação do ID token com `google-auth`, seguindo as regras do Admin SDK:
    - RS256 com os certificados do `securetoken`, em cache pelo `max-age`;
    - `aud` e `iss` do projeto, `exp`/`iat` e `sub`;
    - revogação pelo `validSince` da conta (Identity Toolkit `accounts:lookup`), só em `DELETE /me`.

    Devolve `Identity(uid, email, email_verified, name, sign_in_provider)`. Com
    `FIREBASE_AUTH_EMULATOR_HOST` (proibido em `prd`), aceita os tokens sem assinatura do emulador,
    mas ainda confere as claims.

    **Por que não o `firebase-admin`:** ele traz o `googleapiclient` (+110 MB), e a imagem passava de
    442 MB (limite de 300 MB, F01-RT-05). Sem ele, a imagem ficou com 291 MB, depois de trocar também o
    `uvicorn[standard]` por `uvicorn` + `uvloop` + `httptools`.
  - `core/errors.py`: Problem Details (`application/problem+json`), com `type` estável
    (`unauthenticated`, `email-not-verified`, …).
  - `api/deps.py`: dependência `current_user()`; lê só o header `Authorization: Bearer`. Conta
    `password` sem `email_verified` → 403.
  - `repositories/users.py`: cliente Firestore do banco `settings.firestore_database` (`specflow`);
    `get_or_create`, `export` (documento + subcoleções, recursivo) e `delete` (`recursive_delete`).
  - `services/account.py`: perfil, exportação e exclusão. Não chama `auth.delete_user` nem
    `revoke_refresh_tokens`, porque o Auth é compartilhado (F03-RT-04).
  - `api/v1/me.py`: `GET /api/v1/me`, `GET /api/v1/me/export`, `DELETE /api/v1/me`.
  - Dependências novas: `google-cloud-firestore`, `google-auth[requests]` e `cryptography`.
- **Front:**
  - `@firebase/app` + `@firebase/auth` (não o pacote `firebase`, que traz o Firestore com um
    `@grpc/grpc-js` vulnerável) e `react-router` para as rotas; TanStack Query para `/me`;
  - `AuthProvider` (`onAuthStateChanged`) e `<ProtectedRoute>`;
  - páginas `/login`, `/cadastro`, `/recuperar-senha` e `/conta`;
  - o cliente da API injeta `Authorization` e, em 401, renova o token (`getIdToken(true)`) e tenta uma vez.
- **Config do Firebase no SPA:** variáveis `VITE_FIREBASE_*`.
  - **Local:** apontam para o projeto `demo-functional-agent` dos emuladores (`VITE_FIREBASE_AUTH_EMULATOR`).
  - **Produção:** o `make deploy-web` lê a config do web app na API do Firebase
    (`webApps/{id}/config`) e passa ao build. O `apiKey` não fica no git, porque o `gitleaks` o
    marcaria, embora seja público.
- **Contrato (Art. V):** `scripts/export_openapi.py` gera `frontend/openapi.json`, e
  `npm run gen:api` gera `src/lib/api-schema.d.ts`. O CI falha se algum dos dois estiver
  desatualizado (`make api-types` regenera).
- **Dados:** `users/{uid}` `{displayName, email, createdAt, locale}` no banco `specflow`.
- **Infra:** nenhuma mudança no Terraform. Provedores e domínios do Auth são do projeto compartilhado
  (F02-RT-09). O domínio `specsflow-ai.web.app` é incluído pelo PO no console.
- **Rollback:** reverter a revisão (runbook). Os perfis são aditivos.

### 9. Plano de testes
| Camada | O que cobre |
|---|---|
| Unitário (back) | `test_authz.py`: matriz rota × token, gerada por introspecção do app FastAPI. Cobre sem token, malformado, expirado, de outro projeto, e-mail não verificado e válido. Toda rota nova de `/api/**` entra na matriz automaticamente. |
| Integração (back) | `test_me.py` e `test_account_delete.py` no emulador do Firestore. Cobrem perfil no 1º acesso, export, exclusão idempotente e exclusão de 10 mil docs em menos de 30 s. |
| Componente (front) | Vitest + MSW: rotas protegidas, formulários, retry em 401 (F03-RT-03) |
| E2E | Playwright contra `make dev` (emuladores): AT-F03-01..04 + axe. O e-mail é verificado pela API REST do emulador (`oobCodes`). Roda num job de CI com docker compose. |
| Manual | M-F03-01 (Google) e M-F03-02 (redefinir senha) em produção |
