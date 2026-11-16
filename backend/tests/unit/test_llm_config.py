"""Provedor, modelo e prompt por variável de ambiente (F05-RT-09, ADR-008)."""

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.fake_llm import EchoChatModel
from app.agent.llm import build_chat_model
from app.core.config import Settings

pytestmark = pytest.mark.req("F05-RT-09")

KMS = "projects/p/locations/l/keyRings/k/cryptoKeys/jira-tokens"


def test_padrao_e_gemini_no_vertex_sem_chave() -> None:
    settings = Settings(env="test", gcp_project="pcb-inspect")
    model = build_chat_model(settings)

    assert isinstance(model, ChatGoogleGenerativeAI)
    assert model.model.endswith("gemini-3.5-flash-lite")
    assert model.vertexai is True
    assert (model.project, model.location) == ("pcb-inspect", "global")
    assert model.google_api_key is None


def test_modelo_e_regiao_vem_do_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "gemini-3.8-flash")
    monkeypatch.setenv("LLM_LOCATION", "us-central1")
    monkeypatch.setenv("PROMPT_VERSION", "v1")
    settings = Settings(env="test")
    model = build_chat_model(settings)

    assert isinstance(model, ChatGoogleGenerativeAI)
    assert model.model.endswith("gemini-3.8-flash")
    assert model.location == "us-central1"
    assert settings.prompt_version == "v1"


def test_projeto_do_vertex_separado_do_firebase_no_local() -> None:
    settings = Settings(env="local", gcp_project="demo-functional-agent", llm_project="pcb-inspect")
    model = build_chat_model(settings)

    assert isinstance(model, ChatGoogleGenerativeAI)
    assert model.project == "pcb-inspect"


def test_variavel_vazia_nao_apaga_o_padrao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "")
    assert Settings(env="test").llm_model == "gemini-3.5-flash-lite"


def test_modelo_de_eco_so_fora_de_producao() -> None:
    assert isinstance(build_chat_model(Settings(env="local", llm_provider="fake")), EchoChatModel)
    with pytest.raises(ValueError, match="LLM_PROVIDER=fake só com ENV local/test"):
        Settings(env="prd", llm_provider="fake", kms_key_name=KMS)


def test_provedor_desconhecido() -> None:
    class Other:
        llm_provider = "openai"
        llm_model = "x"
        llm_location = "x"
        llm_temperature = 0.0
        gcp_project = "x"
        llm_project = None

    with pytest.raises(ValueError, match="LLM_PROVIDER desconhecido"):
        build_chat_model(Other())
