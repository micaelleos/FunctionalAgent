"""Configuração tipada da aplicação, lida de variáveis de ambiente."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

    env: Literal["local", "test", "dev", "stg", "prd"] = "local"
    app_version: str = Field(default="dev", description="SHA do commit, injetado no build")
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
