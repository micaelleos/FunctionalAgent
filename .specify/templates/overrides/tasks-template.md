---
description: "Template de tarefas do projeto (substitui o tasks-template do Spec Kit)"
---

<!-- Preenchido por /speckit-tasks a partir de plan.md e spec.md.
     Diferenças em relação ao template padrão do Spec Kit:
     - As fases são incrementos organizados pelos requisitos funcionais (Fxx-RF-nn) e cenários de
       aceitação (AT-Fxx-nn) da spec, porque as specs do projeto não usam user stories P1/P2.
       O rótulo [USn] do Spec Kit é substituído pelo ID do requisito, ex.: [F05-RF-01].
     - Testes são OBRIGATÓRIOS (Constituição, Art. VI): cada incremento começa pelos testes.
     - Cada tarefa leva ≤ 1 dia, cita o caminho do arquivo e o teste que a acompanha.
     Mantenha o formato de checklist: /speckit-implement e /speckit-converge leem estas linhas.
     Apague todas as tarefas de exemplo abaixo. -->

# Fxx — <Nome da feature> — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md (obrigatório), spec.md (obrigatório), research.md, data-model.md, contracts/,
quickstart.md

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição em caminho/do/arquivo — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa pendente)
- **[Fxx-RF-nn]**: requisito atendido (RF, ou RT quando a tarefa só serve a um requisito técnico); obrigatório nas fases de incremento, ausente em Preparação,
  Fundação e Validação. Use mais de um ID se a tarefa cobrir vários (`[F05-RF-01][F05-RF-07]`)
- **teste:** o teste que acompanha a tarefa (caminho, `AT-Fxx-nn` ou eval). Testes novos marcados
  com o ID: `@pytest.mark.req("Fxx-RF-nn")` ou o ID no nome do `describe`/`test`
- **est.:** ≤ 1 d (ex.: `0,5 d`). Tarefa maior deve ser dividida

## 8. Tarefas

### Fase 1: Preparação (contrato primeiro)

**Objetivo:** contrato e esqueleto que permitem front e back em paralelo (Art. V).

- [ ] T001 Definir rotas e esquemas de `<rota>` em backend/app/api/v1/<modulo>.py — teste: backend/tests/contract/test_<modulo>.py — 0,5 d
- [ ] T002 [P] Regenerar o cliente TS a partir do OpenAPI em frontend/src/lib/api — teste: CI de contrato — 0,25 d

---

### Fase 2: Fundação (bloqueia os incrementos)

**Objetivo:** peças compartilhadas por todos os requisitos (repositórios, clientes, config, flag).

- [ ] T003 Criar repositório de `<entidade>` em `users/{uid}/…` em backend/app/repositories/<entidade>.py — teste: backend/tests/integration/test_<entidade>_repo.py (emulador) — 0,5 d
- [ ] T004 [P] Adicionar configuração `<VAR>` em backend/app/core/config.py — teste: backend/tests/unit/test_config.py — 0,25 d

**Checkpoint:** fundação pronta; os incrementos podem começar.

---

### Fase 3: Incremento 1 — <título> ([Fxx-RF-01], [Fxx-RF-02])

**Objetivo:** <o que o usuário passa a conseguir fazer>

**Aceitação:** AT-Fxx-01, AT-Fxx-02

#### Testes primeiro (ficam vermelhos até o fim do incremento)

- [ ] T005 [P] [Fxx-RF-01] Cenário AT-Fxx-01 em backend/tests/acceptance/test_fxx_<nome>.py — teste: o próprio — 0,5 d
- [ ] T006 [P] [Fxx-RF-01] Teste de integração do fluxo em backend/tests/integration/test_<nome>.py — teste: o próprio — 0,5 d

#### Implementação

- [ ] T007 [Fxx-RF-01] Implementar caso de uso em backend/app/services/<nome>.py — teste: T006 — 1 d
- [ ] T008 [Fxx-RF-02] Expor rota em backend/app/api/v1/<modulo>.py — teste: T005 — 0,5 d
- [ ] T009 [P] [Fxx-RF-02] Tela/componente em frontend/src/features/<nome>/ — teste: frontend/src/features/<nome>/<Nome>.test.tsx — 0,5 d

**Checkpoint:** AT-Fxx-01..02 verdes localmente.

---

<!-- Repita a fase de incremento para os demais requisitos, em ordem de prioridade (Must antes de
     Should/Could). Cada incremento deve ser testável sozinho. -->

### Fase N: Validação e entrega (Gates 2–4)

**Objetivo:** cumprir a Definition of Done da feature.

- [ ] Tnnn Rodar AT-Fxx-01..nn em dev e registrar o resultado em spec.md §11 Evidências — teste: pipeline de aceitação — 0,5 d
- [ ] Tnnn Atualizar a matriz spec.md §10 Rastreabilidade (nenhum RF sem teste; `make trace` verde) — teste: scripts/trace_requirements.py — 0,25 d
- [ ] Tnnn [P] Instrumentar o indicador da spec §1 (Art. IX) em backend/app/<…> — teste: teste de log/métrica — 0,5 d
- [ ] Tnnn [P] Rodar evals (só se mudou prompt, modelo ou ferramentas) — teste: suíte de evals ≥ baseline — 0,5 d
- [ ] Tnnn [P] Atualizar documentação de usuário e runbook/alertas, se houver nova operação — teste: revisão — 0,25 d

---

## Dependências e paralelismo

- **Preparação → Fundação → Incrementos → Validação.** Incrementos dependem só da Fundação, salvo
  quando indicado na tarefa (`depende de Tnnn`).
- Dentro de um incremento: testes → repositórios/clientes → serviços → rotas → UI.
- Tarefas `[P]` do mesmo incremento podem rodar juntas; front e back podem seguir em paralelo depois
  da Fase 1, usando mocks (MSW) gerados do contrato.

## Estratégia de entrega

1. Fases 1 e 2 → contrato publicado (DoR).
2. Incremento 1 (requisitos Must) → valida AT correspondentes → PR pequeno (≤ 400 linhas idealmente).
3. Demais incrementos, um PR cada, mantendo o CI verde.
4. Fase N → Gate 3 (aceite do PO) e Gate 4 (verificação pós-deploy em até 24 h).
