"""Rotas de conversas (F07): contrato, validação, isolamento e o histórico com os cartões."""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, cast

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.agent.fake_llm import ScriptedChatModel
from app.api.deps import (
    get_action_service,
    get_chat_service,
    get_conversation_service,
    get_verifier,
)
from app.core.config import Settings, get_settings
from app.main import create_app
from app.services.actions import ActionService
from app.services.chat import ChatService
from app.services.conversations import ConversationService
from app.services.jira_connections import JiraConnectionService
from tests.chat_fakes import (
    ISSUE_TYPES_EN,
    NOW,
    FakeJiraService,
    MemoryChatStore,
    call,
    issue_types_response,
)
from tests.fakes import FakeVerifier
from tests.spec_fixtures import pix_story_data

ALICE = {"Authorization": "Bearer ok:alice"}
BOB = {"Authorization": "Bearer ok:bob"}
BASE = "/api/v1/conversations"


def _jira(request: httpx.Request) -> httpx.Response:
    if (types := issue_types_response(request, ISSUE_TYPES_EN)) is not None:
        return types
    if request.url.path == "/rest/api/3/project/search":
        return httpx.Response(200, json={"values": [{"key": "ABC", "name": "Loja"}]})
    return httpx.Response(201, json={"key": "ABC-1"})


@dataclass
class App:
    client: TestClient
    store: MemoryChatStore
    llm: ScriptedChatModel
    title: ScriptedChatModel

    def send(self, conversation: str, text: str, headers: dict[str, str] = ALICE) -> list[Any]:
        with self.client.stream(
            "POST", f"{BASE}/{conversation}/messages", json={"content": text}, headers=headers
        ) as response:
            assert response.status_code == 200, response.read()
            lines = list(response.iter_lines())
        return [json.loads(line[6:]) for line in lines if line.startswith("data: ")]


@pytest.fixture
def app() -> Iterator[App]:
    store = MemoryChatStore()
    fake_jira = cast(JiraConnectionService, FakeJiraService(handler=_jira))
    llm = ScriptedChatModel(responses=[])
    title = ScriptedChatModel(responses=[])
    settings = Settings(env="test")
    chat = ChatService(store, fake_jira, llm, settings, clock=lambda: NOW, title_llm=title)
    actions = ActionService(store, fake_jira, settings, clock=lambda: NOW)
    conversations = ConversationService(store, clock=lambda: NOW)
    api = create_app()
    api.dependency_overrides[get_settings] = lambda: settings
    api.dependency_overrides[get_verifier] = FakeVerifier
    api.dependency_overrides[get_chat_service] = lambda: chat
    api.dependency_overrides[get_action_service] = lambda: actions
    api.dependency_overrides[get_conversation_service] = lambda: conversations
    with TestClient(api) as client:
        yield App(client, store, llm, title)


@pytest.mark.req("F07-RF-01")
@pytest.mark.req("F07-RF-02")
def test_criar_listar_e_abrir(app: App) -> None:
    created = app.client.post(BASE, json={"project_key": "SCRUM"}, headers=ALICE)

    assert created.status_code == 201
    body = created.json()
    assert body | {"id": "x"} == {
        "id": "x",
        "title": "Nova conversa",
        "project_key": "SCRUM",
        "created_at": "2026-11-16T12:00:00Z",
        "updated_at": "2026-11-16T12:00:00Z",
        "message_count": 0,
    }
    page = app.client.get(BASE, headers=ALICE).json()
    assert page == {"items": [body], "next_cursor": None}
    assert app.client.get(f"{BASE}/{body['id']}", headers=ALICE).json() == body


@pytest.mark.req("F07-RT-01")
@pytest.mark.parametrize(
    ("query", "status"),
    [("limit=0", 422), ("limit=51", 422), ("limit=50", 200), ("cursor=%40%40", 400)],
)
def test_limites_da_paginacao(app: App, query: str, status: int) -> None:
    assert app.client.get(f"{BASE}?{query}", headers=ALICE).status_code == status


@pytest.mark.req("F07-RF-06")
@pytest.mark.parametrize(
    "body",
    [{"project_key": "scrum"}, {"project_key": "A"}, {"title": ""}, {"title": "x" * 81}, {"x": 1}],
)
def test_entrada_invalida_e_422(app: App, body: dict[str, Any]) -> None:
    assert app.client.post(BASE, json=body, headers=ALICE).status_code == 422


@pytest.mark.req("F07-RF-04")
@pytest.mark.req("F07-RF-06")
def test_patch_so_muda_o_que_foi_enviado(app: App) -> None:
    cid = app.client.post(BASE, json={"project_key": "SCRUM"}, headers=ALICE).json()["id"]

    renamed = app.client.patch(f"{BASE}/{cid}", json={"title": "Checkout v2"}, headers=ALICE)
    loose = app.client.patch(f"{BASE}/{cid}", json={"project_key": None}, headers=ALICE)
    no_title = app.client.patch(f"{BASE}/{cid}", json={"title": None}, headers=ALICE)

    assert (renamed.json()["title"], renamed.json()["project_key"]) == ("Checkout v2", "SCRUM")
    assert (loose.json()["title"], loose.json()["project_key"]) == ("Checkout v2", None)
    assert no_title.json()["title"] == "Checkout v2"


@pytest.mark.req("F07-RF-03")
def test_conversa_de_outro_usuario_e_404_em_todas_as_rotas(app: App) -> None:
    cid = app.client.post(BASE, json={}, headers=BOB).json()["id"]

    assert app.client.get(BASE, headers=ALICE).json()["items"] == []
    for method, path, body in [
        ("GET", f"{BASE}/{cid}", None),
        ("PATCH", f"{BASE}/{cid}", {"title": "roubada"}),
        ("GET", f"{BASE}/{cid}/messages", None),
    ]:
        response = app.client.request(method, path, json=body, headers=ALICE)
        assert (response.status_code, response.json()["code"]) == (404, "conversation-not-found")
    # Excluir a de outro usuário não apaga nada (o caminho parte do uid do token).
    assert app.client.delete(f"{BASE}/{cid}", headers=ALICE).status_code == 204
    assert app.client.get(f"{BASE}/{cid}", headers=BOB).status_code == 200


@pytest.mark.req("F07-RF-03")
@pytest.mark.req("F07-RF-04")
def test_chat_historico_e_titulo_pela_api(app: App) -> None:
    app.title.responses.append(AIMessage("Pix na loja"))
    app.llm.responses += [
        call("propor_criacao_issue", {"project_key": "ABC", "spec": pix_story_data()}),
        AIMessage("Confirme no cartão."),
    ]
    events = app.send("new", "Crie a story do Pix no ABC")
    cid = next(e["conversation_id"] for e in events if "conversation_id" in e)
    action_id = next(e["action_id"] for e in events if "action_id" in e)
    confirmed = app.client.post(f"/api/v1/actions/{action_id}/confirm", headers=ALICE)
    assert confirmed.status_code == 200

    page = app.client.get(f"{BASE}/{cid}/messages", headers=ALICE).json()

    assert [(m["role"], m["text"]) for m in page["items"]] == [
        ("user", "Crie a story do Pix no ABC"),
        ("assistant", "Confirme no cartão."),
    ]
    [card] = page["items"][1]["actions"]
    assert (card["id"], card["status"], card["result"]["issue_key"]) == (action_id, "done", "ABC-1")
    [listed] = app.client.get(BASE, headers=ALICE).json()["items"]
    # usuário, ferramenta, agente e o aviso de sistema da confirmação (F06)
    assert (listed["title"], listed["message_count"]) == ("Pix na loja", 4)


@pytest.mark.req("F07-RF-05")
def test_excluir_e_404_depois_e_a_acao_some(app: App) -> None:
    app.llm.responses += [
        call("propor_criacao_issue", {"project_key": "ABC", "spec": pix_story_data()}),
        AIMessage("Confirme no cartão."),
    ]
    app.title.responses.append(AIMessage("Pix"))
    events = app.send("new", "Crie a story do Pix no ABC")
    cid = next(e["conversation_id"] for e in events if "conversation_id" in e)
    action_id = next(e["action_id"] for e in events if "action_id" in e)

    assert app.client.delete(f"{BASE}/{cid}", headers=ALICE).status_code == 204
    assert app.client.delete(f"{BASE}/{cid}", headers=ALICE).status_code == 204

    assert app.client.get(f"{BASE}/{cid}", headers=ALICE).status_code == 404
    confirm = app.client.post(f"/api/v1/actions/{action_id}/confirm", headers=ALICE)
    assert (confirm.status_code, confirm.json()["code"]) == (404, "action-not-found")
    assert app.client.get(BASE, headers=ALICE).json()["items"] == []


def test_rotas_exigem_login(app: App) -> None:
    for method, path in [("GET", BASE), ("POST", BASE), ("DELETE", f"{BASE}/x")]:
        assert app.client.request(method, path, json={}).status_code == 401
