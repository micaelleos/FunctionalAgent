# F03 — Autenticação e conta do usuário — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- **Back** (camadas `api → services → repositories → core`):
  - `core/auth.py`: verificação do ID token com `firebase_admin.auth.verify_id_token` (chaves públicas em
    cache pelo SDK; `check_revoked=True` só em `DELETE /me`). Devolve `Identity(uid, email, email_verified,
    name, sign_in_provider)`.
  - `core/errors.py`: Problem Details (`application/problem+json`), com `type` estável
    (`unauthenticated`, `email-not-verified`, …).
  - `api/deps.py`: dependência `current_user()`; lê só o header `Authorization: Bearer`. Conta
    `password` sem `email_verified` → 403.
  - `repositories/users.py`: cliente Firestore do banco `settings.firestore_database` (`specflow`);
    `get_or_create`, `export` (documento + subcoleções, recursivo) e `delete` (`recursive_delete`).
  - `services/account.py`: perfil, exportação e exclusão. Não chama `auth.delete_user` nem
    `revoke_refresh_tokens`, porque o Auth é compartilhado (F03-RT-04).
  - `api/v1/me.py`: `GET /api/v1/me`, `GET /api/v1/me/export`, `DELETE /api/v1/me`.
  - Dependência nova: `firebase-admin`.
- **Front:**
  - SDK `firebase` (só `auth`) e `react-router` para as rotas;
  - `AuthProvider` (`onAuthStateChanged`) e `<ProtectedRoute>`;
  - páginas `/login`, `/cadastro`, `/recuperar-senha` e `/conta`;
  - o cliente da API injeta `Authorization` e, em 401, renova o token (`getIdToken(true)`) e tenta uma vez.
- **Config do Firebase no SPA:** variáveis `VITE_FIREBASE_*`.
  - **Local:** apontam para o projeto `demo-functional-agent` dos emuladores (`VITE_FIREBASE_AUTH_EMULATOR`).
  - **Produção:** o `make deploy-web` lê a config do web app na API do Firebase
    (`webApps/{id}/config`) e passa ao build. O `apiKey` não fica no git, porque o `gitleaks` o
    marcaria, embora seja público.
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
