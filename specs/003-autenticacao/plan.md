# F03 — Autenticação e conta do usuário — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- **Back:** `core/auth.py` com dependência `current_user()` usando `firebase_admin.auth.verify_id_token`
  (cache das chaves públicas); `check_revoked=True` em `DELETE /me`. `services/account.py` (perfil, export, delete).
- **Front:** `AuthProvider` (onAuthStateChanged), `<ProtectedRoute>`, páginas `/login`, `/cadastro`, `/recuperar-senha`,
  `/conta`. Middleware do cliente API injeta `Authorization`.
- **Dados:** `users/{uid}` `{displayName, email, createdAt, locale}`.
- **Infra:** provedores Google e e-mail/senha habilitados via Terraform; domínio autorizado do Hosting.
- **Rollback:** reverter revisão; dados de perfil são aditivos.

### 9. Plano de testes
Matriz de autorização reutilizada por **todas** as features seguintes (cada rota nova entra na matriz automaticamente
via introspecção do app FastAPI).
