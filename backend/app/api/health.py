"""Rota de liveness, sem autenticação (F01-RF-02)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    env: str


# /healthz atende as probes do Cloud Run (dentro do contêiner). Na URL pública *.run.app o front-end
# do Google reserva caminhos terminados em "z" e devolve 404, então clientes externos usam /health.
@router.get("/healthz", response_model=HealthResponse)
@router.get("/health", response_model=HealthResponse)
def healthz(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(status="ok", version=settings.app_version, env=settings.env)
