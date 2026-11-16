# F04 — Conexão Jira por usuário

| Campo | Valor |
|---|---|
| **Status** | Em produção |
| **Fase** | 1 — Núcleo |
| **Dependências** | F03 |
| **ADRs** | ADR-004 |
| **Estimativa** | 5 dias |
| **Gates** | Decisões do PO em 2026-11-16: cifra direta com `kms.encrypt`; aceite contra o Jira sandbox do PO. Aprovação dos Gates 0 e 1 na revisão do PR |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** credenciais Jira digitadas a cada sessão, exibidas em texto puro e mantidas sem proteção (D02).
- **Objetivo:** o usuário cadastra uma vez sua conexão Jira, que é validada e guardada cifrada; o token nunca volta ao navegador.
- **Indicador:** % de conexões com status `ok`; 0 ocorrências de token em logs (verificação automatizada).

### 2. Escopo
- **Inclui:** tela "Configurações" (já desenhada no incremento 0 da F08) ligada à API real; criar, trocar, testar e
  remover a conexão (MVP: 1 conexão por usuário, o modelo já suporta N); validação via `GET /rest/api/3/myself`;
  cifra com Cloud KMS; cliente Jira `httpx` reutilizável (base de F05, F09, F10); estado "inválida" quando o Jira
  recusa o token, com aviso global de reconexão.
- **Fora de escopo:** OAuth Atlassian (F13), Jira Data Center e domínios próprios (só `*.atlassian.net`), listar
  projetos (F09). Os demais métodos do cliente Jira (projetos, busca, criar issue) entram com as features que os usam.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F04-RF-01 | O usuário informa URL do site (`https://<site>.atlassian.net`), e-mail e API token e salva a conexão | Must |
| F04-RF-02 | Ao salvar, o sistema valida a credencial no Jira e mostra o nome da conta Jira em caso de sucesso | Must |
| F04-RF-03 | Credenciais inválidas não são salvas e o usuário vê a causa (URL inválida, credencial recusada, site inacessível) | Must |
| F04-RF-04 | Após salvo, o token é exibido apenas mascarado (`••••1234`) e não pode ser lido de volta | Must |
| F04-RF-05 | O usuário pode substituir a credencial (site, e-mail e token, validados de novo) ou remover a conexão | Must |
| F04-RF-06 | Quando o Jira recusar o token (401) — ao "Testar conexão" ou em qualquer uso futuro —, a conexão fica "inválida" e todas as telas do app mostram o aviso "Sua conexão com o Jira expirou" com "Reconectar" | Must |
| F04-RF-07 | A tela explica como gerar um API token (conteúdo da antiga página "Sobre") | Should |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F04-RT-01 | Token cifrado com Cloud KMS (`jira-tokens`, `encrypt` direto) antes de gravar; Firestore guarda só ciphertext + versão da chave | teste de integração lê o doc cru |
| F04-RT-02 | Nenhuma resposta da API contém o token (nem a exportação de dados da F03); logs não contêm o token | teste de contrato + teste de log |
| F04-RT-03 | URL normalizada (só `https`, só `<site>.atlassian.net`, sem porta nem credenciais, caminho descartado); o cliente não segue redirecionamentos — previne SSRF | unit |
| F04-RT-04 | Cliente Jira: timeouts (connect 5 s, read 20 s), até 3 tentativas com backoff em 429/5xx respeitando `Retry-After` (máx. 10 s) | unit com respx |
| F04-RT-05 | Token decifrado apenas em memória por requisição; nunca armazenado em cache global | revisão + teste |
| F04-RT-06 | Implementação local de cifra (`LocalFernetCipher`) só ativa com `ENV` `local` ou `test`; em `prd` sem `KMS_KEY_NAME` a API não sobe | unit |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Conexão com o Jira

  Cenário: AT-F04-01 Conectar com credencial válida          # F04-RF-01, F04-RF-02, F04-RF-04
    Dado que estou autenticado sem conexão Jira
    Quando informo o site sandbox, o e-mail e o token válidos e clico em "Validar e salvar"
    Então vejo "Conectado como <nome da conta>"
    E o token aparece como "••••" seguido dos 4 últimos caracteres
    E GET /api/v1/jira/connections não contém o token em nenhum campo

  Cenário: AT-F04-02 Credencial inválida não é salva         # F04-RF-03
    Quando informo um token inválido e clico em "Validar e salvar"
    Então vejo "O Jira recusou a credencial. Verifique e-mail e token."
    E nenhuma conexão é criada

  Cenário: AT-F04-03 URL fora do padrão é recusada           # F04-RF-03, F04-RT-03
    Quando informo a URL "http://169.254.169.254"
    Então vejo "Informe uma URL https://<seu-site>.atlassian.net"

  Cenário: AT-F04-04 Token revogado pede reconexão           # F04-RF-06
    Dado uma conexão salva cujo token foi revogado no Jira
    Quando clico em "Testar conexão"
    Então vejo o aviso "Sua conexão com o Jira expirou" com o botão "Reconectar"
    E o aviso aparece também em "Projetos Jira"

  Cenário: AT-F04-05 Remover conexão                          # F04-RF-05
    Quando removo a conexão
    Então "Projetos Jira" mostra "Conecte sua conta do Jira"
```

AT-F04-01, 02, 03 e 05 rodam no Playwright contra `make dev` e o Jira sandbox do PO (`JIRA_SANDBOX_*` no
`.env.local`; fora do CI). AT-F04-04 precisa de um token revogado: automatizado com Jira simulado (respx no
backend, Vitest no front) e conferido à mão no roteiro M-F04-01 (revogar um token de teste no Atlassian).

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| II Privacidade | Conexão em `users/{uid}/jira_connections`; exportada sem o ciphertext e apagada com a conta (F03) |
| III Segredos | KMS; token nunca no cliente nem em logs |
| X UX | Mensagens de erro acionáveis |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F04-RF-01 | AT-F04-01, `test_jira_connections_api.py` | ✅ (AT no sandbox em 2026-11-16) |
| F04-RF-02 | AT-F04-01, `test_jira_connections_api.py` | ✅ (AT no sandbox em 2026-11-16) |
| F04-RF-03 | AT-F04-02, AT-F04-03, `test_jira_connections_api.py`, `test_jira_urls.py` | ✅ (AT no sandbox em 2026-11-16) |
| F04-RF-04 | AT-F04-01, `test_jira_connections_api.py` | ✅ (AT no sandbox em 2026-11-16) |
| F04-RF-05 | AT-F04-05, `test_jira_connections_api.py` | ✅ (AT no sandbox em 2026-11-16) |
| F04-RF-06 | AT-F04-04 (`test_jira_connections_api.py`, `jira.test.tsx`), M-F04-01 | ✅ (M-F04-01 em produção em 2026-11-16) |
| F04-RF-07 | `jira.test.tsx` (painel "Como criar o token") | ✅ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
| 2026-11-16 | `b779943` (master) | `make dev` (emuladores + API local) + Jira sandbox do PO, projeto SCRUM | `E2E_EMULATORS=1 npx playwright test f04-jira.spec.ts` (AT-F04-01, 02, 03, 05) | 2 passed | PO (2026-11-16) |
| 2026-11-16 | `44ae63e8db77` (deploy) | Produção (https://specsflow-ai.web.app) + Jira sandbox do PO | Roteiro manual M-F04-01: conectar, revogar o token no Atlassian, "Test connection" | Conexão marcada como expirada; aviso "Your Jira connection has expired" com "Reconnect" | PO (2026-11-16) |
