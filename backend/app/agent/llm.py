"""Fábrica do modelo de chat do agente (F05-RT-09, ADR-008).

Gemini no Vertex AI pelo `ChatGoogleGenerativeAI` (`vertexai=True`), autenticado pelas credenciais
padrão do ambiente: a conta de serviço no Cloud Run, o ADC do PO na máquina local. Não há chave de
LLM. Trocar de modelo é só mudar `LLM_MODEL`.
"""

from typing import Protocol

from langchain_core.language_models import BaseChatModel

from app.agent.fake_llm import EchoChatModel


class LlmSettings(Protocol):
    @property
    def llm_provider(self) -> str: ...
    @property
    def llm_model(self) -> str: ...
    @property
    def llm_location(self) -> str: ...
    @property
    def llm_temperature(self) -> float: ...
    @property
    def gcp_project(self) -> str: ...
    @property
    def llm_project(self) -> str | None: ...


def build_chat_model(settings: LlmSettings) -> BaseChatModel:
    if settings.llm_provider == "fake":
        # `make dev` sem GCP: ecoa a mensagem, sem ferramentas (proibido fora de local/test).
        return EchoChatModel()
    if settings.llm_provider != "google_vertexai":
        raise ValueError(f"LLM_PROVIDER desconhecido: {settings.llm_provider}")
    from langchain_google_genai import ChatGoogleGenerativeAI  # import pesado só quando usado

    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        vertexai=True,
        project=settings.llm_project or settings.gcp_project,
        location=settings.llm_location,
        temperature=settings.llm_temperature,
        # O endpoint global usa cota compartilhada (DSQ): 429 é esperado em picos; a lib
        # repete com espera exponencial.
        max_retries=4,
        timeout=60,
        streaming=True,
    )
