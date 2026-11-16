# F04 — Conexão Jira por usuário — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 6 tarefas · 5 d. T002 reduzida a `myself` + base (retries, timeouts, erros); os outros métodos do
cliente entram com F05/F09/F10.

## 8. Tarefas

### Fase 1: Fundação

**Objetivo:** Cifra de credenciais e cliente Jira reutilizável (usado por F05, F09, F10).

- [x] T001 `Cipher` KMS/local + config (F04-RT-01, F04-RT-06) — teste: `test_crypto.py` — 0,5 d
- [x] T002 `normalize_site_url` + `JiraClient` (`myself`, retries, timeouts, erros) (F04-RT-03, F04-RT-04) — teste: `test_jira_urls.py`, `test_jira_client.py` (respx) — 1 d

---

### Fase 2: Incremento 1 — conexão Jira

**Objetivo:** O usuário cadastra, valida, troca e remove a conexão; token nunca volta ao navegador.

**Aceitação:** AT-F04-01..05

- [x] T003 [F04-RF-01][F04-RF-02][F04-RF-03][F04-RF-04][F04-RF-05][F04-RF-06] Repositório, serviço e rotas `/api/v1/jira/connections`; exportação sem ciphertext — teste: `unit/test_jira_connections_api.py` (inclui redação de logs), `integration/test_jira_connections.py` (emuladores) — 1 d
- [x] T004 [P] [F04-RF-01][F04-RF-03][F04-RF-04][F04-RF-05][F04-RF-06][F04-RF-07] `createHttpProductApi`, tela de configurações e aviso global de reconexão — teste: `jira.test.tsx` (Vitest + MSW) — 1 d

---

### Fase 3: Validação e entrega

**Objetivo:** Cenários de aceitação contra o Jira sandbox e em produção.

**Aceitação:** AT-F04-01..05

- [ ] T005 E2E AT-F04-01/02/03/05 contra `make dev` + Jira sandbox — teste: `e2e/f04-jira.spec.ts` (Playwright; escrito, aguardando `JIRA_SANDBOX_URL`/`_EMAIL` no `.env.local`) — 0,5 d
- [ ] T006 Deploy, roteiro manual M-F04-01 (conectar em produção, revogar token, ver "Reconectar") e evidências — teste: manual — 1 d
