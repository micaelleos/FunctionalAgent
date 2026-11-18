# F12 — Go-live e desativação do Streamlit — Tarefas

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

**Entradas:** plan.md, spec.md · convertido da tabela §8 original para o formato do
`tasks-template` do projeto (checklist lido por `/speckit-implement` e `/speckit-converge`).

## Formato: `- [ ] Tnnn [P?] [Fxx-RF-nn?] Descrição — teste: <teste> — <est.>`

- **[P]**: pode rodar em paralelo · **[Fxx-RF-nn]**: requisito atendido · **teste:** o teste que
  acompanha a tarefa · caminhos dos arquivos: ver plan.md §7

**Total:** 7 tarefas · 4 d + 1 semana de beta. Revisão 2026-11-18: sem redirecionamento (o Streamlit
não estava publicado), página de privacidade (T002), AT-F12-01 com debug token do App Check (T004),
checklist e restauração separados (T005), remoção do legado em PR próprio (T006/T007).

## 8. Tarefas

### Fase 1: Preparação (PR 1)

**Objetivo:** ajuda, privacidade, beta e o AT-F12-01 prontos para o Dia D.

**Aceitação:** AT-F12-03

- [x] T001 [F12-RF-03] About com o fluxo novo, suporte e link de privacidade — teste: `AboutPage.test.tsx`, AT-F12-03 — 0,5 d
- [x] T002 [P] [F12-RF-04] Página pública `/privacy` ligada no About, cadastro e landing — teste: `PrivacyPage.test.tsx`, AT-F12-03 — 0,5 d
- [x] T003 [P] Checklist de prontidão e roteiro do beta (`docs/go-live/`) — teste: revisão do PO — 0,5 d
- [x] T004 [F12-RF-01] AT-F12-01 em Playwright para prd com debug token do App Check — teste: `e2e/f12-golive.spec.ts` (escrito; roda no Dia D, T005) — 0,5 d

---

### Fase 2: Beta e Dia D

**Objetivo:** convidados usam o app por 1 semana; checklist completo e AT-F12-01 verde em prd.

**Aceitação:** AT-F12-01

- [ ] T005 Beta (2026-11-19 → 25), F11-T008 (`enforce`), ensaio de restauração, evals ≥ baseline, AT-F12-01 em prd, checklist 100% — teste: AT-F12-01, `evals/run.py --compare` — 1 d

---

### Fase 3: Remoção do legado (PR 3, D+7)

**Objetivo:** Streamlit fora do repositório; o repo leva ao app novo.

**Aceitação:** AT-F12-02

- [ ] T006 [F12-RF-02] Tag `legacy-streamlit-final`, `prompt_2` congelado em `evals/`, remoção de `legacy/` e `make legacy` — teste: `scripts/test_no_legacy.py`, evals baseline — 0,5 d
- [ ] T007 [F12-RF-02] README novo; CLAUDE.md, CONTRIBUTING e Constituição sem o Streamlit — teste: AT-F12-02 — 0,5 d
