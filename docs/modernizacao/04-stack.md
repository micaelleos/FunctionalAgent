# 04 — Stack tecnológica

> Versões são as linhas principais recomendadas na data do plano. Fixe as versões exatas no lockfile ao
> iniciar a F01 e atualize via Dependabot.

## 1. Frontend

| Tecnologia | Papel | Por que |
|---|---|---|
| **React 19 + TypeScript (strict)** | UI | Requisito do projeto; tipagem evita classes inteiras de bugs |
| **Vite** | Build/dev server | Rápido, gera SPA estático ideal para Firebase Hosting |
| **React Router** | Rotas | Padrão de mercado para SPA |
| **TanStack Query** | Estado de servidor | Cache, refetch, estados de loading/erro sem boilerplate |
| **Tailwind CSS + shadcn/ui (Radix)** | Design system | Componentes acessíveis, código no repo (sem lock-in) |
| **react-markdown + remark-gfm + rehype-sanitize** | Render das respostas | Markdown seguro (tabelas, listas, código) |
| **Firebase JS SDK** (`auth`, `app-check`) | Login e App Check | Somente identidade; nenhum acesso direto ao Firestore |
| **openapi-typescript + openapi-fetch** | Cliente API | Tipos gerados do contrato OpenAPI (Artigo V) |
| **@microsoft/fetch-event-source** | SSE com POST e headers | `EventSource` nativo não envia `Authorization` |
| **Zod + React Hook Form** | Formulários | Validação declarativa (ex.: conexão Jira) |
| **Vitest + Testing Library + MSW** | Testes unit/componente | Rápido, mocks de rede realistas |
| **Playwright + @axe-core/playwright** | E2E + acessibilidade | Teste final de aceitação das features |
| **ESLint + Prettier** | Qualidade | Padronização |

## 2. Backend

| Tecnologia | Papel | Por que |
|---|---|---|
| **Python 3.12** | Linguagem | Requisito; ecossistema de IA |
| **uv** | Dependências/lockfile | Instalação rápida e reprodutível (`uv.lock`) |
| **FastAPI + Uvicorn** | API HTTP/SSE | Async, OpenAPI automático, Pydantic nativo |
| **Pydantic v2 + pydantic-settings** | Modelos e config | Validação e configuração tipadas |
| **google-genai** (Gemini no Vertex AI) | Agente | SDK oficial; loop próprio com streaming e chamadas de função, sem chave de LLM ([ADR-008](adr/ADR-008-llm-gemini-vertex.md)) |
| **httpx** | Cliente Jira | Async, timeouts, fácil de mockar (`respx`); substitui `atlassian-python-api` (síncrono) |
| **google-cloud-firestore** (async) / **firebase-admin** | Dados e verificação de token | SDKs oficiais |
| **google-cloud-kms**, **google-cloud-secret-manager** | Criptografia/segredos | Artigo III |
| **structlog** + **OpenTelemetry** (exporter Cloud Trace) | Observabilidade | Logs JSON compatíveis com Cloud Logging, traces distribuídos |
| **tenacity** | Retries | Backoff em 429/5xx do Jira e do LLM |
| **pytest, pytest-asyncio, respx, freezegun, coverage** | Testes | — |
| **Ruff, mypy (strict), import-linter** | Qualidade | Lint/format, tipagem, regras de camadas |

## 3. Plataforma

| Serviço | Uso |
|---|---|
| **Firebase Hosting** | SPA, CDN global, canais de preview por PR |
| **Firebase Authentication** | Google Sign-In + e-mail/senha |
| **Firebase App Check** | Proteção da API contra clientes não legítimos |
| **Cloud Run** | Backend (container), escala a zero, revisões com divisão de tráfego |
| **Firestore (modo nativo)** | Dados por usuário |
| **Artifact Registry** | Imagens Docker |
| **Secret Manager** | Segredos do sistema (o LLM no Vertex AI usa a conta de serviço, sem chave) |
| **Vertex AI** | Modelos Gemini do agente (ADR-008) |
| **Cloud KMS** | Chave simétrica para tokens Jira dos usuários |
| **Cloud Logging / Monitoring / Trace / Error Reporting** | Observabilidade |
| **Terraform (provider google/google-beta)** | IaC; estado em bucket GCS versionado |
| **GitHub Actions + Workload Identity Federation** | CI/CD sem chaves |

## 4. Ferramentas locais

- **Firebase Emulator Suite** (Auth + Firestore) via `docker compose up`.
- `make dev` sobe emuladores + backend com reload + frontend Vite.
- **pre-commit**: ruff, prettier, eslint, gitleaks.

## 5. O que sai da stack

| Sai | Substituído por |
|---|---|
| Streamlit | React + Vite |
| `AgentExecutor`, `ConversationBufferMemory`, `format_tool_to_openai_function` | Loop próprio com `google-genai` + histórico no Firestore (ADR-008) |
| `atlassian-python-api` | Cliente httpx próprio, API v3 com ADF |
| `.env` com chaves reais | Secret Manager (prd) / `.env.local` só com emuladores (dev) |
| `requirements.txt` sem versões | `pyproject.toml` + `uv.lock` |
