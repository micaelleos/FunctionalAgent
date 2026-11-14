"""Ponto de entrada da API do Agente Funcional."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Agente Funcional API",
        version=settings.app_version,
        docs_url="/docs" if settings.env in {"local", "dev"} else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Firebase-AppCheck"],
    )
    app.include_router(health.router)
    return app


app = create_app()
