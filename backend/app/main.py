"""Ponto de entrada da API do Agente Funcional."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.api.v1 import chat, jira, me
from app.core.config import get_settings
from app.core.errors import install_problem_handlers


def create_app() -> FastAPI:
    settings = get_settings()
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
        expose_headers=["X-Conversation-Id", "X-Sse-Schema-Version"],
    )
    install_problem_handlers(app)
    app.include_router(health.router)
    app.include_router(me.router)
    app.include_router(jira.router)
    app.include_router(chat.router)
    return app


app = create_app()
