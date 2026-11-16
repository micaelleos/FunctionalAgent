"""Configuração tipada da aplicação, lida de variáveis de ambiente."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Variáveis vazias (ex.: `LLM_MODEL=` no .env.local) não apagam os padrões.
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore", env_ignore_empty=True)

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

    kms_key_name: str | None = Field(
        default=None,
        description="Chave KMS dos tokens do Jira (projects/…/cryptoKeys/jira-tokens); F04-RT-01",
    )
    local_cipher_key: str | None = Field(
        default=None,
        description="Chave Fernet da cifra local (só ENV local/test); vazia = chave fixa de dev",
    )

    # Agente (F05, ADR-008): Gemini no Vertex AI, autenticado pela SA do Cloud Run (sem chave).
    llm_provider: Literal["google_vertexai", "fake"] = Field(
        default="google_vertexai", description="`fake` só em local/test (LLM roteirizado)"
    )
    llm_model: str = "gemini-3.5-flash-lite"
    llm_location: str = Field(default="global", description="Região do Vertex AI")
    llm_project: str | None = Field(
        default=None,
        description="Projeto do Vertex AI; vazio = GCP_PROJECT (local: emulador ≠ projeto real)",
    )
    llm_temperature: float = 0.2
    # Preço por milhão de tokens, para o custo estimado por turno (F05-RT-10).
    llm_price_input_per_mtok: float = 0.30
    llm_price_output_per_mtok: float = 2.50
    prompt_version: str = "v1"
    # F06: desligar mantém as propostas guardadas, sem executar nenhuma (rollback do plano).
    actions_enabled: bool = True
    agent_max_iterations: int = Field(default=8, description="Iterações de ferramenta por turno")
    agent_turn_timeout_s: float = 240.0
    history_token_budget: int = Field(
        default=12_000, description="Orçamento do histórico; acima disso, sumarização (RT-07)"
    )

    @model_validator(mode="after")
    def _sem_llm_fake_em_producao(self) -> "Settings":
        if self.llm_provider == "fake" and self.env not in {"local", "test"}:
            raise ValueError("LLM_PROVIDER=fake só com ENV local/test")
        return self

    @model_validator(mode="after")
    def _sem_emulador_em_producao(self) -> "Settings":
        if self.env == "prd" and self.auth_emulator_host:
            raise ValueError("FIREBASE_AUTH_EMULATOR_HOST não pode ser usado em produção")
        return self

    @model_validator(mode="after")
    def _cifra_de_verdade_fora_do_local(self) -> "Settings":
        # F04-RT-06: fora de local/test, o token do Jira só pode ser cifrado pelo KMS.
        if self.env not in {"local", "test"} and not self.kms_key_name:
            raise ValueError(f"KMS_KEY_NAME é obrigatório com ENV={self.env}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
