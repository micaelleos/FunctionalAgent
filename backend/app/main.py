"""Ponto de entrada da API do Agente Funcional."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.api.v1 import (
    actions,
    chat,
    client_errors,
    conversations,
    jira,
    jira_issues,
    jira_projects,
    me,
)
from app.core.config import get_settings
from app.core.errors import install_problem_handlers
from app.core.logging import RequestContextMiddleware, configure_logging
from app.core.telemetry import configure_tracing


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.gcp_project)
    configure_tracing(
        enabled=settings.tracing_enabled,
        project=settings.gcp_project,
        version=settings.app_version,
        ratio=settings.tracing_sample_ratio,
    )
    app = FastAPI(
        title="SpecFlow AI API",
        version=settings.app_version,
        docs_url="/docs" if settings.env in {"local", "dev"} else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Firebase-AppCheck"],
        expose_headers=["X-Conversation-Id", "X-Sse-Schema-Version", "X-Request-Id", "Retry-After"],
    )
    # Fora do CORS: o request_id e o trace valem também para as respostas de erro do CORS.
    app.add_middleware(RequestContextMiddleware)
    install_problem_handlers(app)
    app.include_router(health.router)
    app.include_router(me.router)
    app.include_router(jira.router)
    app.include_router(jira_projects.router)
    app.include_router(jira_issues.router)
    app.include_router(chat.router)
    app.include_router(actions.router)
    app.include_router(conversations.router)
    app.include_router(client_errors.router)
    return app


app = create_app()
