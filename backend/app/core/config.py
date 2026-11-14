"""Configuração tipada da aplicação, lida de variáveis de ambiente."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

    env: Literal["local", "test", "dev", "stg", "prd"] = "local"
    app_version: str = Field(default="dev", description="SHA do commit, injetado no build")
    cors_origins: list[str] = ["http://localhost:5173"]
    gcp_project: str = Field(
        default="demo-functional-agent",
        description="Projeto do Firebase/GCP (aud do token); o padrão é o dos emuladores",
    )
    firestore_database: str = Field(default="specflow", description="Banco Firestore do app")
    auth_emulator_host: str | None = Field(
        default=None,
        validation_alias="FIREBASE_AUTH_EMULATOR_HOST",
        description="Emulador de Auth (aceita tokens sem assinatura); proibido em prd",
    )

    @model_validator(mode="after")
    def _sem_emulador_em_producao(self) -> "Settings":
        if self.env == "prd" and self.auth_emulator_host:
            raise ValueError("FIREBASE_AUTH_EMULATOR_HOST não pode ser usado em produção")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
