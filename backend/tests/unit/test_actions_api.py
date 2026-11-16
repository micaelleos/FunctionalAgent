"""Rotas de confirmação (F06): do cartão proposto no chat até a issue criada, via API."""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, cast

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.agent.fake_llm import ScriptedChatModel
from app.api.deps import get_action_service, get_chat_service, get_verifier
from app.core.config import Settings, get_settings
from app.main import create_app
from app.services.actions import ActionService
from app.services.chat import ChatService
from app.services.jira_connections import JiraConnectionService
from tests.chat_fakes import (
    ISSUE_TYPES_EN,
    NOW,
    SITE,
    FakeJiraService,
    MemoryChatStore,
    call,
    issue_types_response,
)
from tests.fakes import FakeVerifier
from tests.spec_fixtures import pix_story_data

ALICE = {"Authorization": "Bearer ok:alice"}
BOB = {"Authorization": "Bearer ok:bob"}


class Jira:
    """Lista o projeto ABC e cria ABC-<n>; registra as escritas."""

    def __init__(self) -> None:
        self.writes: list[httpx.Request] = []
        self.fail_with: httpx.Response | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if (types := issue_types_response(request, ISSUE_TYPES_EN)) is not None:
            return types
        if request.url.path == "/rest/api/3/project/search":
            return httpx.Response(200, json={"values": [{"key": "ABC", "name": "Loja"}]})
        self.writes.append(request)
        if self.fail_with is not None:
            return self.fail_with
        return httpx.Response(201, json={"key": f"ABC-{len(self.writes)}"})


@dataclass
class App:
    client: TestClient
    store: MemoryChatStore
    jira: Jira
    llm: ScriptedChatModel

    def propose(self, headers: dict[str, str] = ALICE) -> tuple[str, str]:
        """Um turno de chat em que o agente propõe a story do Pix; devolve (conversa, ação)."""
        self.llm.responses += [
            call("propor_criacao_issue", {"project_key": "ABC", "spec": pix_story_data()}),
            AIMessage("Confirme no cartão."),
        ]
        with self.client.stream(
            "POST", "/api/v1/conversations/new/messages", json={"content": "Crie"}, headers=headers
        ) as response:
            cid = response.headers["x-conversation-id"]
            lines = list(response.iter_lines())
        [data] = [
            json.loads(lines[i + 1][6:])
            for i, line in enumerate(lines)
            if line == "event: action_proposed"
        ]
        return cid, str(data["action_id"])


@pytest.fixture
def app() -> Iterator[App]:
    jira = Jira()
    store = MemoryChatStore()
    fake_jira = cast(JiraConnectionService, FakeJiraService(handler=jira))
    llm = ScriptedChatModel(responses=[])
    settings = Settings(env="test")
    chat = ChatService(store, fake_jira, llm, settings, clock=lambda: NOW)
    actions = ActionService(store, fake_jira, settings, clock=lambda: NOW)
    api = create_app()
    api.dependency_overrides[get_settings] = lambda: settings
    api.dependency_overrides[get_verifier] = FakeVerifier
    api.dependency_overrides[get_chat_service] = lambda: chat
    api.dependency_overrides[get_action_service] = lambda: actions
    with TestClient(api) as client:
        yield App(client, store, jira, llm)


@pytest.mark.req("F06-RF-02")
@pytest.mark.req("F06-RF-04")
def test_proposta_no_chat_so_vira_issue_depois_de_confirmar(app: App) -> None:
    cid, aid = app.propose()

    [card] = app.client.get(f"/api/v1/conversations/{cid}/actions", headers=ALICE).json()
    assert (card["id"], card["status"], card["kind"]) == (aid, "pending", "create_issue")
    assert card["preview"]["sections"][0]["title"] == "Objetivo"
    assert card["readiness"]["ready"] is True
    assert app.jira.writes == []

    response = app.client.post(f"/api/v1/actions/{aid}/confirm", headers=ALICE)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["result"] == {"issue_key": "ABC-1", "url": f"{SITE}/browse/ABC-1"}
    assert len(app.jira.writes) == 1


@pytest.mark.req("F06-RF-03")
def test_recusar_e_depois_confirmar_da_409(app: App) -> None:
    _, aid = app.propose()

    rejected = app.client.post(f"/api/v1/actions/{aid}/reject", headers=ALICE)
    confirm = app.client.post(f"/api/v1/actions/{aid}/confirm", headers=ALICE)

    assert (rejected.status_code, rejected.json()["status"]) == (200, "rejected")
    assert confirm.status_code == 409
    assert confirm.headers["content-type"] == "application/problem+json"
    assert confirm.json()["code"] == "action-not-pending"
    assert confirm.json()["action"]["status"] == "rejected"
    assert app.jira.writes == []


@pytest.mark.req("F06-RT-04")
def test_outro_usuario_nao_ve_nem_confirma(app: App) -> None:
    cid, aid = app.propose()

    assert app.client.post(f"/api/v1/actions/{aid}/confirm", headers=BOB).status_code == 404
    assert app.client.post(f"/api/v1/actions/{aid}/reject", headers=BOB).status_code == 404
    assert app.client.get(f"/api/v1/conversations/{cid}/actions", headers=BOB).json() == []
    assert app.jira.writes == []


@pytest.mark.req("F06-RT-05")
def test_expirada_da_410(app: App) -> None:
    _, aid = app.propose()
    [doc] = next(iter(app.store.actions.values()))
    doc["expiresAt"] = NOW - timedelta(seconds=1)

    response = app.client.post(f"/api/v1/actions/{aid}/confirm", headers=ALICE)

    assert (response.status_code, response.json()["code"]) == (410, "action-expired")
    assert response.json()["action"]["status"] == "expired"


@pytest.mark.req("F06-RF-07")
def test_erro_do_jira_da_422_com_a_mensagem_traduzida(app: App) -> None:
    _, aid = app.propose()
    app.jira.fail_with = httpx.Response(403)

    response = app.client.post(f"/api/v1/actions/{aid}/confirm", headers=ALICE)

    body: dict[str, Any] = response.json()
    assert (response.status_code, body["code"]) == (422, "jira-forbidden")
    assert body["detail"] == "Você não tem permissão para criar issues no projeto ABC."
    assert body["action"]["error"]["code"] == "jira-forbidden"
