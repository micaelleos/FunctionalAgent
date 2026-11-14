# Comandos do monorepo. Requer: make, Docker, uv e Node 22 (no Windows, use WSL ou Git Bash).
.PHONY: help install dev dev-down lint format test coverage build trace legacy infra-check test-rules e2e e2e-local api-types deploy deploy-api deploy-web

help:            ## Lista os comandos
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

install:         ## Instala dependências de backend e frontend
	cd backend && uv sync
	cd frontend && npm ci
	cd infra/firestore-rules && npm ci

dev:             ## Sobe emuladores + backend + frontend (http://localhost:5173)
	docker compose up --build

dev-down:        ## Derruba o ambiente local
	docker compose down

lint:            ## Lint, formatação, tipos e regras de camadas
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports
	cd frontend && npm run lint && npm run format:check && npm run typecheck

format:          ## Formata o código
	cd backend && uv run ruff format . && uv run ruff check --fix .
	cd frontend && npm run format

test:            ## Testes com cobertura mínima (back 80%, front 70%); sobe os emuladores do Firebase
	docker compose up -d emulators
	@until curl -fs localhost:8081 >/dev/null && curl -fs localhost:9099 >/dev/null; do sleep 1; done
	cd backend && FIREBASE_AUTH_EMULATOR_HOST=localhost:9099 FIRESTORE_EMULATOR_HOST=localhost:8081 uv run pytest --cov --cov-report=term-missing
	cd frontend && npm run coverage

build:           ## Build da imagem do backend e do SPA
	docker build -t functional-agent-api:local backend
	cd frontend && npm run build

infra-check:     ## Terraform fmt/validate/tflint, sem credenciais (F02)
	cd infra/terraform && terraform fmt -check -recursive && terraform init -backend=false -input=false >/dev/null && terraform validate && tflint --init >/dev/null && tflint --recursive --config "$$PWD/.tflint.hcl"

test-rules:      ## Regras do Firestore no emulador via Docker (AT-F02-04)
	docker compose build emulators
	docker run --rm --user "$$(id -u):$$(id -g)" -e HOME=/tmp -v "$$PWD":/workspace -w /workspace/infra/firestore-rules functionalagent-emulators npm run test:emulator

e2e:             ## Aceitação Playwright (E2E_BASE_URL; padrão http://localhost:5173)
	cd frontend && npx playwright test

e2e-local:       ## Aceitação com emuladores (rode `make dev` antes): AT-F03 e AT-F02
	cd frontend && E2E_EMULATORS=1 npx playwright test

api-types:       ## Exporta o OpenAPI do backend e gera os tipos do cliente TS (Constituição V)
	cd backend && uv run python ../scripts/export_openapi.py
	cd frontend && npm run gen:api

deploy:          ## Deploy manual em produção: API e depois o frontend
deploy: deploy-api deploy-web

deploy-api:      ## Build/push da imagem, revisão sem tráfego, smoke e 100% do tráfego
	scripts/deploy.sh api

deploy-web:      ## Build do SPA e publicação no Firebase Hosting (specsflow-ai.web.app)
	scripts/deploy.sh web

trace:           ## Verifica que todo requisito tem teste (rastreabilidade)
	python3 scripts/trace_requirements.py

legacy:          ## Roda o app Streamlit antigo (até o go-live, F12)
	cd legacy && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && python -m streamlit run main.py
