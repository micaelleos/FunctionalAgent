# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Agente Funcional: an AI agent that helps Product Owners write functional documentation (epics, BDD
user stories, tasks) and export it to Jira. The project is **mid-migration** from a Streamlit
prototype (`legacy/`, kept until go-live in F12, no new features) to a React SPA (`frontend/`) +
FastAPI backend (`backend/`) on Firebase Hosting + Cloud Run + Firestore. Only F01 (monorepo,
tooling, CI) is implemented so far; most backend packages are empty placeholders for later
features. Docs, specs, and UI text are in **pt-BR**.

## Commands

Prerequisites: uv 0.11+, Node 22, Docker, make.

```bash
make install   # uv sync (backend) + npm ci (frontend)
make dev       # docker compose: Firebase emulators (UI :4000, Auth :9099, Firestore :8081) + API :8000 + Vite :5173
make lint      # ruff check/format --check, mypy strict, lint-imports, eslint, prettier --check, tsc
make format
make test      # backend pytest --cov (fail_under 80) + frontend vitest coverage (70)
make trace     # every functional requirement in specs/ must be referenced by a test
make legacy    # old Streamlit app
make infra-check  # terraform fmt/validate + tflint (no GCP credentials needed)
make test-rules   # Firestore rules tests in the emulator container (Docker)
make e2e          # Playwright acceptance tests; E2E_BASE_URL (+ E2E_EXPECTED_VERSION) target a deployed env
```

Without Docker:
```bash
cd backend && uv run uvicorn app.main:app --reload   # http://localhost:8000/healthz, /docs in local/dev
cd frontend && npm run dev                            # VITE_API_BASE_URL defaults to http://localhost:8000
```

Single tests:
```bash
cd backend && uv run pytest tests/unit/test_health.py::test_name
cd frontend && npx vitest run src/App.test.tsx -t "pattern"
# trace-script tests (run like CI does, outside backend's pytest config):
uv run --project backend pytest -q scripts --rootdir scripts -p no:cacheprovider -o addopts=""
```

## Architecture

- **Backend layering is enforced** by import-linter (`backend/pyproject.toml`):
  `app.main → app.api → app.services → (app.agent | app.integrations | app.repositories) → app.core`.
  `api` never touches Firestore/Jira directly; `agent` knows nothing about HTTP and gets
  dependencies injected per request; `core` imports nothing above it. A reverse import fails `make lint`.
- App is built by `create_app()` in `app/main.py`; config is `pydantic-settings` in
  `app/core/config.py` (`get_settings()` is `lru_cache`d; reads env and `.env.local`).
- **Firestore is backend-only**: `firestore.rules` denies all client access. All user data lives
  under `users/{uid}/…` and is accessed only after verifying the Firebase ID token. No per-user
  state in process globals (this was the legacy app's main bug).
- **Human-in-the-loop for Jira writes**: agent tools that create/update/move/delete in Jira only
  produce a *proposed action*; execution happens after explicit UI confirmation, enforced in code
  (ADR-003), and the executed payload must equal the confirmed one.
- Frontend calls Cloud Run directly (not via a Hosting rewrite) because the chat streams over SSE
  and Hosting rewrites cap at 60 s (ADR-002). The TS API client is meant to be generated from the
  FastAPI OpenAPI schema; breaking API changes go to a new `/api/vN` prefix.
- Target design (agent graph, tools, SSE event schema, Firestore model, API v1) is in
  `docs/modernizacao/03-arquitetura.md`; decisions in `docs/modernizacao/adr/`.

## Spec-driven workflow (Spec Kit)

- Constitution (non-negotiable rules, Articles I–XI): `.specify/memory/constitution.md`.
  `docs/modernizacao/02-constituicao.md` is a mirror; amend both in the same PR.
- Each feature `Fxx` lives in `specs/0xx-slug/` (`F05` → `specs/005-agente-chat-api/`):
  `spec.md` (requirements, Gherkin acceptance tests, constitution check, traceability, evidence),
  `plan.md`, `tasks.md`. Index, status, and dependencies: `specs/ROADMAP.md`.
- Requirement IDs: `Fxx-RF-nn` (functional), `Fxx-RT-nn` (technical), acceptance scenarios
  `AT-Fxx-nn`. Tag tests with them: `@pytest.mark.req("F05-RF-01")` (pytest runs with
  `--strict-markers`) or the ID in a Vitest/Playwright `describe`/`test` name.
- `scripts/trace_requirements.py` parses `specs/*/spec.md` (the `**Status**` row, `| Fxx-RF-nn |`
  table rows, and the `### 10. Rastreabilidade` section). It fails CI only for specs whose status
  is "Em validação", "Aceita" or "Em produção". Keep those headings/formats intact when editing specs.
- `/speckit-specify`, `/speckit-plan` and `/speckit-tasks` use project overrides in
  `.specify/templates/overrides/` ({spec,plan,tasks}-template.md). In generated `tasks.md`, the
  Spec Kit `[USn]` label is replaced by the requirement ID (`[F05-RF-01]`), tests are mandatory,
  and each task names its test and an estimate ≤ 1 day; keep the `- [ ] Tnnn` checklist format,
  which `/speckit-implement` and `/speckit-converge` parse. Scope changes during implementation must update the spec in
  the same PR.

## Infrastructure and delivery (F02)

- The app ("SpecFlow AI", https://specsflow-ai.web.app) lives in the **shared portfolio GCP/Firebase
  project `pcb-inspect`**, with a single environment (production) plus per-PR previews. Every resource
  it owns is prefixed `specflow` (Cloud Run `specflow-api`, Firestore database `specflow`, AR repo,
  KMS keyring, SAs, WIF pool). Never touch the `(default)` Firestore database, project-wide
  Auth/Identity Platform config, budgets, or other apps' resources (F02-RT-09).
- Terraform root module in `infra/terraform/` (`envs/prd.tfvars`, state in
  `gs://pcb-inspect-tfstate` prefix `specflow/prd`). Terraform owns Cloud Run *configuration*; the
  image and traffic belong to the pipeline (`ignore_changes`). The Hosting site was created in the
  console and is adopted via an `import` block. One-time setup: `infra/bootstrap/README.md`.
- WIF only issues credentials to jobs in GitHub Environments `prd`/`preview` (deployer SA) and
  `infra-prd` (terraform SA); a new workflow job that talks to GCP must declare one of them.
- `deploy.yml`: build → `prd` approval → no-traffic revision + smoke → 10% canary judged by
  `scripts/canary.py` → promote or auto-rollback → frontend → Playwright acceptance in prod.
  `preview.yml` (label `preview`) is the pre-prod validation; `infra.yml` applies on master after
  `infra-prd` approval. Shared steps in `.github/actions/`. Deploy/infra jobs are gated by repo
  variables `DEPLOY_ENABLED` / `INFRA_ENABLED`.
- Rollback procedures: `docs/runbooks/rollback.md`.

## Conventions

- Branches `feat/Fxx-slug` from `master`; PRs use `.github/pull_request_template.md` (constitution
  checklist). CI also runs gitleaks, pip-audit/npm audit, a check that no `__pycache__`/`.pyc`/
  `node_modules` is committed, and a Docker image check (< 300 MB, runs as user `app`, `/healthz` smoke).
- Python: 3.12, ruff line length 100, mypy `strict` over `app` and `tests`.
- New infrastructure components (queue, cache, extra DB) or stack changes require an ADR.
