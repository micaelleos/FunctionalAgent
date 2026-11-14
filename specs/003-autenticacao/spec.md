# F03 — Autenticação e conta do usuário

| Campo | Valor |
|---|---|
| **Status** | Em implementação |
| **Fase** | 1 — Núcleo |
| **Dependências** | F02 |
| **ADRs** | ADR-001 |
| **Estimativa** | 6,5 dias |
| **Gates** | Gate 0 e Gate 1 aprovados pelo dono do produto em 2026-11-14 |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** qualquer pessoa com a URL usa o app e a chave do LLM (D03); não há noção de "usuário".
- **Objetivo:** login com Google ou e-mail/senha; toda a API exige identidade; usuário pode exportar e excluir seus dados.
- **Indicador:** 0 requisições à API sem token válido aceitas (métrica de 401 vs 2xx).

### 2. Escopo
- **Inclui:** telas de login/cadastro/recuperar senha, rotas protegidas no React, verificação de ID token no FastAPI,
  `GET/DELETE /api/v1/me`, `GET /api/v1/me/export`, perfil criado no 1º acesso, configuração pública do
  Firebase injetada no SPA pelo `make deploy`.
- **Fora de escopo:** papéis/admin, workspaces de equipe, SSO corporativo (SAML), allowlist de e-mails, cota de
  uso do LLM por usuário (entra na F05), textos dos e-mails do Auth (são do projeto compartilhado), multi-tenancy.
- **Decisões do PO (2026-11-14):**
  - **Auth compartilhado:** o Firebase Auth é o do projeto `pcb-inspect`, compartilhado pelos apps do
    portfólio. O login (e-mail, senha, `uid`) vale em todos os apps; os **dados** do SpecFlow ficam só no
    banco `specflow`. Provedores, política de senha, domínios autorizados e modelos de e-mail são do projeto e
    não são alterados por este app (F02-RT-09); e-mail/senha e Google já estão habilitados.
  - **Excluir conta apaga só os dados do SpecFlow AI**, não o login nem as sessões dos outros apps.
  - **Cadastro aberto** a qualquer pessoa; o uso do LLM terá cota diária por usuário (F05).
  - **E2E nos emuladores** de Auth e Firestore (local e CI); em produção, só roteiro manual após o `make deploy`.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F03-RF-01 | O usuário pode entrar com conta Google | Must |
| F03-RF-02 | O usuário pode se cadastrar e entrar com e-mail e senha; contas de e-mail só usam o app após verificar o e-mail | Must |
| F03-RF-03 | O usuário pode redefinir a senha por e-mail | Must |
| F03-RF-04 | Rotas do app (exceto login, cadastro, recuperar senha e "Sobre") redirecionam para login quando não autenticado | Must |
| F03-RF-05 | No primeiro acesso é criado o perfil `users/{uid}` com nome, e-mail e data | Must |
| F03-RF-06 | O usuário pode sair (logout) de qualquer página | Must |
| F03-RF-07 | O usuário pode baixar um JSON com todos os seus dados do SpecFlow AI | Should |
| F03-RF-08 | O usuário pode excluir sua conta do SpecFlow AI após confirmar digitando "EXCLUIR": todos os seus dados no banco `specflow` são apagados e ele é deslogado; a tela avisa que o login do portfólio continua valendo nos outros apps | Must |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F03-RT-01 | Toda rota `/api/**` valida o ID token (assinatura, `aud`/`iss` do projeto, expiração; revogação em `DELETE /me`) | matriz de autorização (rota × token) |
| F03-RT-02 | `uid` vem **somente** do token; parâmetros de corpo/rota/query nunca definem o usuário | teste "`?uid=` de B é ignorado" + matriz |
| F03-RT-03 | Token renovado automaticamente no front (SDK) e reenviado em 401 uma vez | teste de componente |
| F03-RT-04 | Exclusão: `recursive_delete(users/{uid})` no banco `specflow`; **não** chama `auth.delete_user` nem `revoke_refresh_tokens` (afetariam os outros apps); idempotente; < 30 s para 10 mil docs | integração com emulador |
| F03-RT-05 | Respostas de erro no formato Problem Details (`application/problem+json`) | contrato |
| F03-RT-06 | Telas de login acessíveis (axe sem violações sérias) | E2E |
| F03-RT-07 | Conta de e-mail/senha sem `email_verified` recebe 403 (`email-not-verified`) nas rotas `/api/**` | teste de autorização |
| F03-RT-08 | A config pública do Firebase (apiKey, authDomain, appId…) entra no SPA no build do `make deploy`, lida da API do Firebase; não é commitada | teste do build + revisão |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Autenticação e conta

  Cenário: AT-F03-01 Acesso sem login é redirecionado         # F03-RF-04
    Dado que não estou autenticado
    Quando abro "/chat"
    Então sou levado para "/login"

  Cenário: AT-F03-02 Cadastro e login por e-mail              # F03-RF-02, F03-RF-05, F03-RF-06
    Quando me cadastro com "e2e-<rand>@teste.dev"
    Então vejo o aviso para verificar o e-mail
    Quando confirmo o e-mail e entro com essas credenciais
    Então vejo meu nome no menu do usuário
    E GET /api/v1/me retorna meu e-mail
    Quando clico em "Sair"
    Então volto para "/login"

  Cenário: AT-F03-03 API recusa chamadas sem identidade válida  # F03-RT-01, F03-RT-02, F03-RT-07
    Quando chamo GET /api/v1/me sem token, com token expirado ou de outro projeto
    Então recebo 401 em Problem Details
    Quando chamo com token de conta de e-mail não verificada
    Então recebo 403
    Quando o usuário A chama GET /api/v1/me?uid=<uid de B>
    Então recebe os dados de A

  Cenário: AT-F03-04 Exportar e excluir conta                 # F03-RF-07, F03-RF-08
    Dado que estou autenticado e tenho perfil
    Quando baixo "Meus dados"
    Então o arquivo JSON contém meu perfil
    Quando excluo minha conta digitando "EXCLUIR"
    Então sou deslogado e "users/{uid}" não existe no banco "specflow"
    Quando entro de novo com o mesmo login
    Então começo com um perfil novo e sem dados anteriores
```
Manual (produção, após `make deploy`): login com Google (M-F03-01) e e-mail de redefinição (M-F03-02) — roteiro de 2 min.
Antes do roteiro, o PO inclui `specsflow-ai.web.app` nos domínios autorizados do Auth (console).

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| II Privacidade | `uid` do token, caminhos `users/{uid}`, exportação e exclusão (LGPD) dos dados do app |
| III Segredos | Config pública do Firebase no front, sem segredo; nada commitado |
| V API-first | Contrato de `/api/v1/me*` no OpenAPI antes do front |
| VI Testes | Matriz de autorização reutilizada por todas as features seguintes |
| X UX/Acessibilidade | axe nas telas de login; textos pt-BR; aviso claro na exclusão |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F03-RF-01 | Roteiro manual M-F03-01; `frontend/src/auth/auth.test.tsx` (botão Google) | 🟡 falta o manual |
| F03-RF-02 | AT-F03-02 (`frontend/e2e/f03-auth.spec.ts`), `backend/tests/unit/test_authz.py` (e-mail não verificado → 403) | ✅ local |
| F03-RF-03 | Roteiro manual M-F03-02; `frontend/src/auth/auth.test.tsx` | 🟡 falta o manual |
| F03-RF-04 | AT-F03-01, `frontend/src/auth/auth.test.tsx` | ✅ local |
| F03-RF-05 | AT-F03-02, `backend/tests/integration/test_me.py::test_perfil_criado_no_primeiro_acesso` | ✅ local |
| F03-RF-06 | AT-F03-02, `frontend/src/auth/auth.test.tsx` | ✅ local |
| F03-RF-07 | AT-F03-04, `backend/tests/integration/test_me.py::test_export_inclui_perfil_e_subcolecoes` | ✅ local |
| F03-RF-08 | AT-F03-04, `backend/tests/integration/test_account_delete.py` | ✅ local |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
