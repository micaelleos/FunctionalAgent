# F06 — Confirmação humana antes de escrever no Jira — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho
- **API** (`api/v1/actions.py`): `POST /api/v1/actions/{id}/confirm` → `200 ActionOut` (`status: done`, `result {issue_key, url}`)
  | `409 action-not-pending` (já concluída, recusada ou em execução; o corpo traz `action`) | `410 action-expired`
  | `422 <código jira-*>` (`detail` = erro traduzido, `action` com o novo estado) | `503 actions-disabled`.
  `POST /api/v1/actions/{id}/reject` → `200`. `GET /api/v1/conversations/{id}/actions` reidrata os cartões.
- **Estados** (`services/actions.py`): `pending → executing → done | failed`; `pending → rejected | expired`.
  A transição roda numa transação do Firestore (`repositories/actions.py`, `max_attempts=10`); quem perde a disputa
  recebe 409 com o estado atual. `executing` há mais de 2 min (processo caiu) vira `failed` incerto.
- **Execução sem LLM** (RT-03): confere `payloadHash`, deriva os campos com `jira_create_fields`/`jira_update_fields`
  (ADF renderizado do `AgentReadySpec`, RT-07) e escreve só na conexão e no site gravados na proposta
  (`connectionId`, `siteUrl`); conexão trocada → `failed` (`jira-connection-changed`).
- **Escrita no Jira** (`JiraClient._write`): nunca repete depois de enviada; só 429 é repetido. 403 numa escrita é
  falta de permissão (`JiraForbiddenError`), não credencial inválida; 401 invalida a conexão (F04).
- **Tradução** (`translate`): permissão, prioridade/pai/tipo inválidos, campos obrigatórios do projeto, issue
  removida, credencial, limite, fora do ar, incerto. Falhas em que o Jira certamente não gravou voltam a `pending`.
- **Ao concluir**: `jira_issues/{key}` (criações; base da F10), mensagem `role=system` na conversa e log
  `jira_write` (uid, action_id, kind, result, issue_key, code; sem conteúdo).
- **Agente**: a cada turno, o prompt de sistema traz "Ações propostas nesta conversa (estado atual)" — é assim que
  ele responde "você recusou" (RF-03). Uma única instrução de sistema (o Gemini aceita só uma).
- **Proposta (F05)**: a prévia passa a ter `sections`, `project_name`, `priority`, `before` (atualizações) e a ação
  grava `connectionId`/`siteUrl`; `propor_atualizacao_issue` aceita `summary` (só o título).
- **Front**: `<ActionCard>` (pendente, enviando, concluída, falhou, recusada, expirada) com a spec por seção
  (`Markdown.tsx`, sem HTML do agente), prontidão e antes/depois; `createHttpProductApi` liga confirmar/recusar. O
  chat continua desligado em produção até a F08.
- **Rollback:** `ACTIONS_ENABLED=false` mantém as propostas sem execução (503).

### 9. Plano de testes
- Unit: `test_actions.py` (execução exata, 10 confirmações paralelas, hash, 404 de outro usuário, expiração,
  tradução, auditoria), `test_jira_write.py` (sem repetição), `test_actions_api.py` (rotas), `test_chat_service.py`
  (estado das ações no prompt), `test_tools_propose.py`; Vitest `ActionCard.test.tsx`, `actions.test.ts`.
- Integração (emulador): transação real com 10 confirmações e execução com o LLM desligado.
- Aceitação AT-F06-01..07 (`tests/acceptance/test_f06_actions.py`): API local + Gemini + Jira sandbox; apaga
  tudo o que cria.
- Evals de injeção (`injection_*`): o agente ao ler gera no máximo propostas, nunca escrita.
