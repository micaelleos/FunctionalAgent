# F12 — Go-live e desativação do Streamlit

| Campo | Valor |
|---|---|
| **Status** | Em implementação (beta de 2026-11-19 a 2026-11-25) |
| **Fase** | 3 — Produção |
| **Dependências** | F01–F11 (F11-T008, App Check em `enforce`, em 2026-11-25) |
| **Estimativa** | 4 dias de trabalho + 1 semana de beta |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Revisão 2026-11-18 (decisões do PO):** o Streamlit nunca foi publicado (rodava só local), então não há
endereço antigo a redirecionar: o RF-02 passa a ser o repositório e o README levando ao app novo. O beta
com convidados fica. Não há domínio próprio (fica `https://specsflow-ai.web.app`, HTTPS do Hosting). O
go-live fecha depois do App Check em `enforce` (2026-11-25). Entra uma página simples de privacidade e
uso. O AT-F12-01 roda no projeto `SCRUM` do Jira sandbox e mantém os issues como evidência. Não há
lista de convite em código: a URL já é pública e cotas (F11) + App Check limitam abuso e custo.

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Objetivo:** abrir o app novo para os convidados do beta, provar em produção que ele faz tudo o que o
  Streamlit fazia, publicar ajuda e privacidade e remover o Streamlit do repositório.
- **Indicador:** 0 incidentes Sev1 na semana do beta e na semana seguinte ao go-live; todos os convidados
  do beta concluem o roteiro (criar ao menos 1 issue no próprio Jira) ou dizem por que não.

### 2. Escopo
- **Inclui:** checklist de prontidão; beta com convidados (roteiro, convite, coleta de feedback); página
  rodapé da página inicial com ajuda (GitHub) e status da API; página de privacidade e uso; AT-F12-01 em prd;
  remoção de `legacy/`, tag `legacy-streamlit-final`, README novo.
- **Fora de escopo:** migração de dados do Streamlit (não há dados persistidos); domínio próprio;
  redirecionamento (o Streamlit não estava publicado); lista de convite no código.

**Ajuste 2026-11-20 (PO):** entra o teto mensal de tokens do beta para o app inteiro (F12-RF-05), e os
alertas por e-mail da F11 saem por custo (dashboard, uptime check e SLO ficam).

**Ajuste 2026-11-18 (PO):** a página "About" saiu ("não tem nada de relevante"). O status e a versão da
API (F01-RF-03, F02-RF-03), o link de ajuda e o de privacidade ficam no rodapé da página inicial;
`/about` leva à página inicial. No chat, em telas largas, mensagens e lista de conversas rolam cada uma
no seu contêiner; o ícone da aba é o logo da landing.

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F12-RF-01 | Todas as capacidades do app antigo existem no novo (matriz de paridade abaixo) | Must |
| F12-RF-02 | Quem chega pelo repositório (README, descrição do GitHub) é levado ao app novo; o Streamlit sai do repositório | Should |
| F12-RF-03 | O rodapé da página inicial diz onde pedir ajuda ("Help", issues do GitHub), liga a privacidade e mostra o status da API; `/about` (antigo) leva à página inicial | Must |
| F12-RF-04 | Página pública "Privacy" (`/privacy`, ligada no rodapé da página inicial e no cadastro): que dados guardamos (conta, conexão Jira com token cifrado, conversas, issues criados, uso diário), com quem são processados (Google Gemini no Vertex AI, Atlassian), o que os logs têm (`uid_hash`, nunca o conteúdo), e como apagar tudo (Account → Delete my data) | Must |
| F12-RF-05 | Teto global do beta: o app inteiro (soma de todos os usuários) usa no máximo `MONTHLY_TOKEN_BUDGET` tokens do Gemini por mês de Brasília (5 milhões ≈ US$ 3,50). Atingido, o chat responde 429 `beta-budget-exhausted` com a data de volta (dia 1º, 00:00 de Brasília) para todos, sem gastar a cota diária; o chat mostra a mensagem sem "Try again". `0` desliga | Must |

**Matriz de paridade**

| Capacidade antiga | Onde está no novo | Teste |
|---|---|---|
| Chat com agente | F05 + F08 | AT-F05-01, AT-F08-01 |
| Criar issue no Jira | F05 + F06 | AT-F06-01 |
| Atualizar issue | F06 | AT-F06-05 |
| Consultar issue / JQL / projetos | F05 | AT-F05-03 |
| Lista de projetos | F09 | AT-F09-01 |
| Issues criados | F10 | AT-F10-01 |
| Configurar credenciais Jira | F04 | AT-F04-01 |
| Página Sobre (status da API) | F12-RF-03 (rodapé da página inicial) | `LandingPage.test.tsx`, `App.test.tsx` |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F12-RT-01 | Checklist de prontidão (abaixo) 100% marcado, com evidência em cada item | revisão do PO |
| F12-RT-02 | AT-F12-01 em prd com uma conta de teste (Jira sandbox, projeto `SCRUM`) por Playwright; o App Check em `enforce` é atendido por um *debug token* do App Check, guardado só no `.env.local` | `e2e/f12-golive.spec.ts` |
| F12-RT-03 | `legacy/` removido; nenhuma dependência nem alvo do Streamlit no repo (Makefile, docs de uso); o baseline das evals continua rodando com o `prompt_2` congelado em `evals/` | `scripts/test_no_legacy.py` no CI |
| F12-RT-04 | Tag `legacy-streamlit-final` no último commit com `legacy/`; README novo (o que é, link do app, arquitetura, como rodar); CLAUDE.md, CONTRIBUTING e Constituição (Art. com `legacy/`, nos dois espelhos) sem o Streamlit | revisão |

**Checklist de prontidão** (`docs/go-live/checklist.md`, um item por linha com a evidência):
SLO, dashboard e uptime check ativos (F11; alertas por e-mail removidos pelo PO em 2026-11-20) · restauração do Firestore ensaiada (PITR para um banco temporário,
`docs/runbooks/firestore-restauracao.md`) · runbooks revisados · evals ≥ baseline (`evals/run.py --compare`)
· ZAP sem achados altos (F11-RT-10) · custo estimado por mês aprovado pelo PO · privacidade publicada
(F12-RF-04) · App Check em `enforce` (F11-T008) · HTTPS (Hosting e Cloud Run; sem domínio próprio) ·
contato de suporte no rodapé (F12-RF-03).

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Go-live

  Cenário: AT-F12-01 Jornada completa em produção               # F12-RF-01, F12-RT-02
    Dado uma conta de teste em produção conectada ao Jira sandbox
    E o App Check em "enforce"
    Quando faço login, peço um épico e uma story para o projeto "SCRUM" e confirmo as duas ações
    Então os dois issues existem no Jira
    E aparecem em "Issues"
    E a conversa está disponível após sair e entrar de novo

  Cenário: AT-F12-02 O repositório leva ao app novo            # F12-RF-02, F12-RT-03
    Quando abro o README do repositório
    Então o primeiro link é https://specsflow-ai.web.app
    E não existe `legacy/` nem instrução de rodar o Streamlit

  Cenário: AT-F12-03 Ajuda e privacidade públicas              # F12-RF-03, F12-RF-04
    Quando abro /about sem estar logado
    Então vou para a página inicial
    E o rodapé tem "Help" (issues do GitHub), "Privacy" e "API: ok"
    E "Privacy" abre /privacy sem login

  Cenário: AT-F12-04 Teto mensal do beta                       # F12-RF-05
    Dado o teto do mês já atingido pela soma dos usuários
    Quando envio uma mensagem no chat
    Então recebo 429 "beta-budget-exhausted" com Retry-After
    E vejo "The beta has used this month's usage limit. Chat is back on the 1st (Brasília time)." sem "Try again"
    E no dia 1º (Brasília) o chat volta a responder
```

### 6. Conformidade com a Constituição
| Artigo | Como esta feature cumpre |
|---|---|
| II Privacidade | A página de privacidade descreve exatamente o que o código guarda; exclusão de conta já existe (F03) |
| III Segredos | Conta de teste e debug token do App Check só no `.env.local`; nunca em logs nem no repo |
| IV Humano no circuito | AT-F12-01 confirma as duas ações pela UI |
| VI Testes | Cada RF tem teste (E2E em prd, componentes, checagem do legado no CI) |
| VIII Infra | Debug token registrado fora do repo; nenhuma infra nova (o teto mensal é uma variável do Cloud Run e um documento no Firestore do app; os alertas saem do Terraform) |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F12-RF-01 | Matriz de paridade, AT-F12-01 (`e2e/f12-golive.spec.ts`) | ⬜ |
| F12-RF-02 | AT-F12-02, `scripts/test_no_legacy.py` | ⬜ |
| F12-RF-03 | AT-F12-03 (`e2e/f12-paginas.spec.ts`), `LandingPage.test.tsx` | ✅ local |
| F12-RF-04 | AT-F12-03 (`e2e/f12-paginas.spec.ts`), `PrivacyPage.test.tsx` | ✅ local |
| F12-RF-05 | AT-F12-04: `tests/unit/test_usage.py`, `tests/integration/test_usage.py`, `ChatPage.test.tsx` | ✅ local |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
| 2026-11-18 | branch `feat/F12-go-live` | local (`make dev`) | AT-F12-03 (About com os 4 passos e o suporte; Privacy pública; axe sem violações sérias); suíte E2E local (19 passaram, 9 pulados); `make lint`; `make test` (backend 593, frontend 149); `make trace` | ✅ | — |
| 2026-11-18 | branch `fix/F12-ajustes-ui` | local (`make dev`) | Ajustes do PO: favicon = logo da landing; About removido (rodapé com Help, Privacy e status da API; `/about` → `/`); chat em tela larga com rolagem própria nas mensagens e na lista de conversas (E2E novo em `f08-chat.spec.ts`: a página não rola, a lateral fica parada). Suíte E2E local 20 passaram, 9 pulados; Vitest 150 | ✅ | — |
| 2026-11-20 | `c0ef0c7` (merge do PR #33) | prd | `terraform apply` (0 criados, 1 alterado, 7 removidos: 6 alertas + canal de e-mail) e `make deploy`: API `specflow-api-00019-9h4` (smoke ok; rollback `specflow-api-00018-bx2`) com `MONTHLY_TOKEN_BUDGET=5000000`; `/health` com a versão, 401 sem token, sem erros nos logs; SPA publicado | ✅ | — |
