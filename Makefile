# Comandos do monorepo. Requer: make, Docker, uv e Node 22 (no Windows, use WSL ou Git Bash).
.PHONY: help install dev dev-down lint format test coverage build trace legacy

help:            ## Lista os comandos
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

install:         ## Instala dependências de backend e frontend
	cd backend && uv sync
	cd frontend && npm ci

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

test:            ## Testes com cobertura mínima (back 80%, front 70%)
	cd backend && uv run pytest --cov --cov-report=term-missing
	cd frontend && npm run coverage

build:           ## Build da imagem do backend e do SPA
	docker build -t functional-agent-api:local backend
	cd frontend && npm run build

trace:           ## Verifica que todo requisito tem teste (rastreabilidade)
	python3 scripts/trace_requirements.py

legacy:          ## Roda o app Streamlit antigo (até o go-live, F12)
	cd legacy && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && python -m streamlit run main.py
