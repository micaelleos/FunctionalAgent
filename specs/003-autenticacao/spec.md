# F03 — Autenticação e conta do usuário

| Campo | Valor |
|---|---|
| **Status** | Rascunho |
| **Fase** | 1 — Núcleo |
| **Dependências** | F02 |
| **ADRs** | ADR-001 |
| **Estimativa** | 5 dias |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** qualquer pessoa com a URL usa o app e a chave do LLM (D03); não há noção de "usuário".
- **Objetivo:** login com Google ou e-mail/senha; toda a API exige identidade; usuário pode exportar e excluir seus dados.
- **Indicador:** 0 requisições à API sem token válido aceitas (métrica de 401 vs 2xx).

### 2. Escopo
- **Inclui:** telas de login/cadastro/recuperar senha, rotas protegidas no React, verificação de ID token no FastAPI,
  `GET/DELETE /api/v1/me`, `GET /api/v1/me/export`, perfil criado no 1º acesso.
- **Fora de escopo:** papéis/admin, workspaces de equipe, SSO corporativo (SAML).

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F03-RF-01 | O usuário pode entrar com conta Google | Must |
| F03-RF-02 | O usuário pode se cadastrar e entrar com e-mail e senha, com verificação de e-mail | Must |
| F03-RF-03 | O usuário pode redefinir a senha por e-mail | Must |
| F03-RF-04 | Rotas do app (exceto login e "Sobre") redirecionam para login quando não autenticado | Must |
| F03-RF-05 | No primeiro acesso é criado o perfil `users/{uid}` com nome, e-mail e data | Must |
| F03-RF-06 | O usuário pode sair (logout) de qualquer página | Must |
| F03-RF-07 | O usuário pode baixar um JSON com todos os seus dados | Should |
| F03-RF-08 | O usuário pode excluir a conta após confirmar digitando "EXCLUIR"; todos os dados e o login são apagados | Must |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F03-RT-01 | Toda rota `/api/**` valida o ID token (assinatura, `aud`, `iss`, expiração, revogação em rotas sensíveis) | testes de autorização |
| F03-RT-02 | `uid` vem **somente** do token; parâmetros de corpo/rota nunca definem o usuário | teste "token de A acessando dados de B" → 404 |
| F03-RT-03 | Token renovado automaticamente no front (SDK) e reenviado em 401 uma vez | teste de componente |
| F03-RT-04 | Exclusão de conta: `recursiveDelete(users/{uid})` + `auth.delete_user`; idempotente; concluída em < 30 s para 10 mil docs | integração com emulador |
| F03-RT-05 | Respostas de erro no formato Problem Details | contrato |
| F03-RT-06 | Telas de login acessíveis (axe sem violações sérias) | E2E |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Autenticação e conta

  Cenário: AT-F03-01 Acesso sem login é redirecionado         # F03-RF-04
    Dado que não estou autenticado
    Quando abro "/chat"
    Então sou levado para "/login"

  Cenário: AT-F03-02 Cadastro e login por e-mail              # F03-RF-02, F03-RF-05, F03-RF-06
    Quando me cadastro com "e2e-<rand>@teste.dev" e confirmo o e-mail
    E entro com essas credenciais
    Então vejo meu nome no menu do usuário
    E GET /api/v1/me retorna meu e-mail
    Quando clico em "Sair"
    Então volto para "/login"

  Cenário: AT-F03-03 API recusa chamadas sem token ou de outro usuário  # F03-RT-01, F03-RT-02
    Quando chamo GET /api/v1/me sem token
    Então recebo 401
    Quando o usuário A chama GET /api/v1/conversations/{id de B}
    Então recebe 404

  Cenário: AT-F03-04 Exportar e excluir conta                 # F03-RF-07, F03-RF-08
    Dado que tenho uma conversa salva
    Quando baixo "Meus dados"
    Então o arquivo JSON contém a conversa
    Quando excluo minha conta digitando "EXCLUIR"
    Então sou deslogado, não consigo mais entrar e "users/{uid}" não existe
```
Manual: login com Google (F03-RF-01) e e-mail de redefinição (F03-RF-03) — roteiro de 2 min no ambiente dev.

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| II Privacidade | `uid` do token, caminhos `users/{uid}`, exportação e exclusão (LGPD) |
| III Segredos | Config pública do Firebase no front; nada secreto |
| X UX/Acessibilidade | axe nas telas de login |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F03-RF-01 | Roteiro manual M-F03-01 | ⬜ |
| F03-RF-02 | AT-F03-02 | ⬜ |
| F03-RF-03 | Roteiro manual M-F03-02 | ⬜ |
| F03-RF-04 | AT-F03-01 | ⬜ |
| F03-RF-05 | AT-F03-02, `test_me.py::test_profile_created_on_first_access` | ⬜ |
| F03-RF-06 | AT-F03-02 | ⬜ |
| F03-RF-07 | AT-F03-04 | ⬜ |
| F03-RF-08 | AT-F03-04, `test_account_delete.py` | ⬜ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
