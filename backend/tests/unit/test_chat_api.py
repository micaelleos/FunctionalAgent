"""Rota SSE do chat e contrato dos eventos (F05-RF-01, F05-RF-07, F05-RT-12)."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.agent.fake_llm import ScriptedChatModel
from app.api.deps import get_chat_service, get_verifier
from app.core.config import Settings, get_settings
from app.main import create_app
from app.services.chat import ChatService
from app.services.chat_events import CHAT_EVENT, SCHEMA_VERSION, json_schema
from app.services.jira_connections import JiraConnectionService
from tests.chat_fakes import NOW, FakeJiraService, MemoryChatStore, call
from tests.fakes import FakeVerifier
from tests.spec_fixtures import pix_story_data

ALICE = {"Authorization": "Bearer ok:alice"}
BOB = {"Authorization": "Bearer ok:bob"}
SCHEMA_FILE = Path(__file__).resolve().parents[3] / "docs" / "api" / "sse-events.v1.json"


@pytest.fixture
def llm() -> ScriptedChatModel:
    return ScriptedChatModel(responses=[])


@pytest.fixture
def client(llm: ScriptedChatModel) -> Iterator[TestClient]:
    app = create_app()
    store = MemoryChatStore()
    service = ChatService(
        store,
        cast(JiraConnectionService, FakeJiraService()),
        llm,
        Settings(env="test"),
        clock=lambda: NOW,
    )
    app.dependency_overrides[get_settings] = lambda: Settings(env="test")
    app.dependency_overrides[get_verifier] = FakeVerifier
    app.dependency_overrides[get_chat_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client


def _events(text: str) -> list[dict[str, Any]]:
    events, current = [], {}
    for line in text.splitlines():
        if line.startswith("event: "):
            current["event"] = line[7:]
        elif line.startswith("data: "):
            current["data"] = json.loads(line[6:])
        elif not line and current:
            events.append(current)
            current = {}
    return events


def _post(client: TestClient, text: str, conversation: str = "new", headers: Any = ALICE) -> Any:
    return client.post(
        f"/api/v1/conversations/{conversation}/messages", json={"content": text}, headers=headers
    )


@pytest.mark.req("F05-RF-01")
@pytest.mark.req("F05-RT-12")
def test_stream_sse_com_eventos_validos_pelo_esquema(
    client: TestClient, llm: ScriptedChatModel
) -> None:
    llm.responses += [
        call("propor_criacao_issue", {"project_key": "ABC", "spec": pix_story_data()}),
        AIMessage("Proposta no cartão."),
    ]
    response = _post(client, "Crie a story do Pix no ABC")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-sse-schema-version"] == str(SCHEMA_VERSION)
    events = _events(response.text)
    kinds = [e["event"] for e in events]
    assert kinds == [
        "tool_start",
        "tool_end",
        "action_proposed",
        "token",
        "token",
        "token",
        "message_saved",
        "done",
    ]
    for event in events:
        CHAT_EVENT.validate_python({"event": event["event"], **event["data"]})
    assert events[-2]["data"]["conversation_id"] == response.headers["x-conversation-id"]


@pytest.mark.req("F05-RT-12")
def test_esquema_publicado_esta_atualizado() -> None:
    # Regenerar com `make api-types` quando um evento mudar (de forma compatível; senão, v2).
    assert json.loads(SCHEMA_FILE.read_text()) == json.loads(
        json.dumps(json_schema(), sort_keys=True, ensure_ascii=False)
    )


def test_conversa_inexistente_e_404_problem_details(client: TestClient) -> None:
    response = _post(client, "oi", conversation="nao-existe")

    assert response.status_code == 404
    assert response.json()["code"] == "conversation-not-found"


def test_conversa_de_outro_usuario_e_404(client: TestClient, llm: ScriptedChatModel) -> None:
    llm.responses.append(AIMessage("oi"))
    cid = _post(client, "oi").headers["x-conversation-id"]

    assert _post(client, "oi", conversation=cid, headers=BOB).status_code == 404


def test_mensagem_vazia_e_sem_token(client: TestClient) -> None:
    assert _post(client, "   ").status_code == 422
    assert _post(client, "oi", headers={}).status_code == 401
