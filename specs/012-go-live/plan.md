# F12 — Go-live e desativação do Streamlit — Plano técnico

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

## Parte B — Plano técnico

### 7. Desenho / sequência

Três PRs, porque o beta e o `enforce` do App Check têm datas:

1. **PR 1 — preparação (2026-11-18/19), branch `feat/F12-go-live`:**
   - Rodapé da landing com "Help" (`https://github.com/micaelleos/FunctionalAgent/issues`), "Privacy" e o
     status da API (`ApiStatus`); a página About saiu (ajuste do PO) e `/about` leva a `/`. `PrivacyPage`
     pública em `/privacy`, ligada também no cadastro. Textos em `i18n/en.ts`.
   - `docs/go-live/checklist.md` (itens do F12-RT-01 com coluna de evidência) e `docs/go-live/beta.md`
     (convite, roteiro de 20 min, perguntas de feedback, como reportar problema).
   - `e2e/f12-golive.spec.ts` (AT-F12-01, só com `E2E_PRD=1`): login com a conta de teste, conversa com
     o Gemini real pedindo um épico e uma story no `SCRUM`, confirma as duas, confere as chaves no
     Jira pela API do sandbox, "Issues" e a conversa após sair e entrar. App Check: o Playwright define
     `self.FIREBASE_APPCHECK_DEBUG_TOKEN` (`addInitScript`) com `E2E_APPCHECK_DEBUG_TOKEN`; o SPA já
     inicializa o App Check e o SDK usa o debug token. O token é registrado no console do Firebase
     (App Check → Apps → Manage debug tokens) pelo PO, nunca no Terraform (o valor iria para o state).
   - Deploy do SPA; início do beta.
2. **Beta (2026-11-19 → 2026-11-25):** convidados seguem `beta.md`; feedback por mensagem ao PO ou
   issue no GitHub. Correções em PRs `fix/F12-*`. Ao fim, F11-T008 (`enforce`) e, no mesmo dia,
   AT-F12-01 em prd, ensaio de restauração do Firestore, evals contra o baseline e o checklist completo.
   Esse é o **Dia D** (go-live): README passa a apontar para o app, a spec vai para "Em validação".
3. **PR 3 — remoção do legado (D+7, ≈ 2026-12-02), branch `chore/F12-remover-legado`:**
   - tag `legacy-streamlit-final` no commit do master antes da remoção;
   - `prompt_2` copiado para `evals/legacy_prompt.txt` (o `legacy_agent.py` passa a ler dali);
   - remove `legacy/`, o alvo `make legacy`, as linhas no CONTRIBUTING/CLAUDE.md, o artigo da
     Constituição que cita `legacy/` (nos dois espelhos, com versão nova);
   - README novo;
   - `scripts/test_no_legacy.py`: falha se existir `legacy/`, `streamlit` em dependências
     (`pyproject.toml`, `requirements*.txt`, `package.json`) ou `make legacy`/`streamlit run` em docs de uso.

**Ensaio de restauração (checklist):** `gcloud firestore export` do `specflow` com `--snapshot-time`
(PITR) para `gs://pcb-inspect-specflow-restore`, `import` num banco `specflow-restore`, leitura de um
documento conhecido, e remoção do banco e do bucket. Custo: centavos (armazenamento por minutos). Pede
aprovação do PO na hora, porque cria recursos em prd.

### 9. Plano de testes
- Componentes: `LandingPage.test.tsx` (rodapé: ajuda, privacidade, status da API; `/about` → `/`), `PrivacyPage.test.tsx`
  (seções, acesso sem login), `routes` (`/privacy` público).
- E2E local: AT-F12-03 contra `make dev` (`e2e/f12-golive.spec.ts`, bloco sem `E2E_PRD`).
- prd: AT-F12-01 (`E2E_PRD=1`), smoke manual de 10 min pelo PO, roteiro do beta.
- CI: `scripts/test_no_legacy.py` (PR 3).
