# F04 — Conexão Jira por usuário

| Campo | Valor |
|---|---|
| **Status** | Rascunho |
| **Fase** | 1 — Núcleo |
| **Dependências** | F03 |
| **ADRs** | ADR-004 |
| **Estimativa** | 5 dias |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** credenciais Jira digitadas a cada sessão, exibidas em texto puro e mantidas sem proteção (D02).
- **Objetivo:** o usuário cadastra uma vez sua conexão Jira, que é validada e guardada cifrada; o token nunca volta ao navegador.
- **Indicador:** % de conexões com status `ok`; 0 ocorrências de token em logs (verificação automatizada).

### 2. Escopo
- **Inclui:** tela "Configurações › Jira", CRUD de conexões (MVP: 1 conexão ativa por usuário, modelo já suporta N),
  validação via `GET /rest/api/3/myself`, cifra com KMS, cliente Jira `httpx` reutilizável, revalidação quando o Jira retorna 401.
- **Fora de escopo:** OAuth Atlassian (F13), Jira Data Center.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F04-RF-01 | O usuário informa URL do site (`https://<site>.atlassian.net`), e-mail e API token e salva a conexão | Must |
| F04-RF-02 | Ao salvar, o sistema valida a credencial no Jira e mostra o nome da conta Jira em caso de sucesso | Must |
| F04-RF-03 | Credenciais inválidas não são salvas e o usuário vê a causa (URL inválida, credencial recusada, site inacessível) | Must |
| F04-RF-04 | Após salvo, o token é exibido apenas mascarado (`••••1234`) e não pode ser lido de volta | Must |
| F04-RF-05 | O usuário pode substituir o token ou remover a conexão | Must |
| F04-RF-06 | Quando o Jira recusar o token (401) durante o uso, a conexão fica "inválida" e o app pede reconexão | Must |
| F04-RF-07 | A tela explica como gerar um API token (conteúdo da antiga página "Sobre") | Should |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F04-RT-01 | Token cifrado com Cloud KMS (`jira-tokens`) antes de gravar; Firestore guarda só ciphertext + versão da chave | teste de integração lê o doc cru |
| F04-RT-02 | Nenhuma resposta da API contém o token; logs e traces não contêm o token (filtro de redação + teste) | teste de contrato + teste de log |
| F04-RT-03 | URL normalizada (sem barra final, apenas `https`, domínio `*.atlassian.net` no MVP) — previne SSRF | unit |
| F04-RT-04 | Cliente Jira: timeouts (connect 5 s, read 20 s), retries com backoff em 429/5xx respeitando `Retry-After` | unit com respx |
| F04-RT-05 | Token decifrado apenas em memória por requisição; nunca armazenado em cache global | revisão + teste |
| F04-RT-06 | Implementação local de cifra (`LocalFernetCipher`) só ativa com `ENV=local` | unit |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Conexão com o Jira

  Cenário: AT-F04-01 Conectar com credencial válida          # F04-RF-01, F04-RF-02, F04-RF-04
    Dado que estou autenticado sem conexão Jira
    Quando informo o site sandbox, o e-mail e o token válidos e clico em "Conectar"
    Então vejo "Conectado como <nome da conta>"
    E o token aparece como "••••" seguido dos 4 últimos caracteres
    E GET /api/v1/jira/connections não contém o token em nenhum campo

  Cenário: AT-F04-02 Credencial inválida não é salva         # F04-RF-03
    Quando informo um token inválido e clico em "Conectar"
    Então vejo "O Jira recusou a credencial. Verifique e-mail e token."
    E nenhuma conexão é criada

  Cenário: AT-F04-03 URL fora do padrão é recusada           # F04-RF-03, F04-RT-03
    Quando informo a URL "http://169.254.169.254"
    Então vejo "Informe uma URL https://<seu-site>.atlassian.net"

  Cenário: AT-F04-04 Token revogado pede reconexão           # F04-RF-06
    Dado uma conexão salva cujo token foi revogado no Jira
    Quando abro "Projetos"
    Então vejo o aviso "Sua conexão com o Jira expirou" com o botão "Reconectar"

  Cenário: AT-F04-05 Remover conexão                          # F04-RF-05
    Quando removo a conexão
    Então "Projetos" mostra "Conecte sua conta do Jira"
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| II Privacidade | Conexão em `users/{uid}/jira_connections` |
| III Segredos | KMS; token nunca no cliente nem em logs |
| X UX | Mensagens de erro acionáveis |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F04-RF-01 | AT-F04-01 | ⬜ |
| F04-RF-02 | AT-F04-01 | ⬜ |
| F04-RF-03 | AT-F04-02, AT-F04-03 | ⬜ |
| F04-RF-04 | AT-F04-01, `test_connections_contract.py` | ⬜ |
| F04-RF-05 | AT-F04-05 | ⬜ |
| F04-RF-06 | AT-F04-04 | ⬜ |
| F04-RF-07 | Revisão de conteúdo | ⬜ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
