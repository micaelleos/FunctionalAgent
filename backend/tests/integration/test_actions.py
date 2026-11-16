"""Confirmação com Firestore e Auth dos emuladores (F06-RT-01, RT-03, RT-05; T001 a T003).

A transação real do Firestore garante uma única execução com confirmações em paralelo, e a
execução funciona com o modelo de linguagem desligado.
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, cast

import httpx
import pytest
from fastapi.testclient import TestClient
from google.cloud import firestore
from langchain_core.messages import AIMessage

from app.agent.fake_llm import ScriptedChatModel
from app.agent.spec.jira_payload import create_payload, payload_hash
from app.api import deps
from app.core.config import Settings
from app.core.errors import ApiProblemError
from app.repositories.actions import ActionRepository
from app.services.actions import ActionService
from app.services.jira_connections import JiraConnectionService
from tests.chat_fakes import FakeJiraService, call
from tests.integration.conftest import DATABASE, PROJECT, AuthEmulator
from tests.spec_fixtures import pix_story, pix_story_data


class Jira:
    def __init__(self) -> None:
        self.writes: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/api/3/project/search":
            return httpx.Response(200, json={"values": [{"key": "ABC", "name": "Loja"}]})
        self.writes.append(request)
        return httpx.Response(201, json={"key": f"ABC-{len(self.writes)}"})


@pytest.fixture
def jira(client: TestClient) -> Jira:
    fake = Jira()
    service = FakeJiraService(handler=fake)
    client.app.dependency_overrides[deps.get_jira_service] = lambda: service  # type: ignore[attr-defined]
    return fake


def _propose(client: TestClient, headers: dict[str, str], llm: ScriptedChatModel) -> str:
    llm.responses += [
        call("propor_criacao_issue", {"project_key": "ABC", "spec": pix_story_data()}),
        AIMessage("Confirme no cartão."),
    ]
    response = client.post(
        "/api/v1/conversations/new/messages", json={"content": "Crie"}, headers=headers
    )
    lines = response.text.splitlines()
    for i, line in enumerate(lines):
        if line == "event: action_proposed":
            return str(json.loads(lines[i + 1][6:])["action_id"])
    raise AssertionError(response.text)


class _NoLlm(ScriptedChatModel):
    async def _agenerate(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("a confirmação chamou o modelo de linguagem")


@pytest.mark.req("F06-RT-03")
@pytest.mark.req("F06-RF-02")
def test_confirmacao_executa_com_o_llm_desligado(
    client: TestClient,
    auth_emulator: AuthEmulator,
    db: firestore.Client,
    jira: Jira,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alice = auth_emulator.create_user()
    llm = ScriptedChatModel(responses=[])
    monkeypatch.setattr(deps, "_chat_model", lambda settings: llm)
    aid = _propose(client, alice.headers, llm)
    monkeypatch.setattr(deps, "_chat_model", lambda settings: _NoLlm(responses=[]))

    response = client.post(f"/api/v1/actions/{aid}/confirm", headers=alice.headers)

    assert response.status_code == 200, response.text
    assert response.json()["result"]["issue_key"] == "ABC-1"
    user = db.collection("users").document(alice.uid)
    action = user.collection("pending_actions").document(aid).get().to_dict() or {}
    assert action["status"] == "done"
    issue = user.collection("jira_issues").document("ABC-1").get().to_dict() or {}
    assert issue["actionId"] == aid
    conversation = action["conversationId"]
    messages = [
        m.to_dict() or {}
        for m in user.collection("conversations")
        .document(conversation)
        .collection("messages")
        .order_by("seq")
        .stream()
    ]
    assert messages[-1]["role"] == "system"
    assert messages[-1]["content"].startswith("O usuário confirmou e o SpecFlow criou ABC-1")
    assert [m["seq"] for m in messages] == list(range(1, len(messages) + 1))


@pytest.mark.req("F06-RT-01")
async def test_dez_confirmacoes_paralelas_na_transacao_real(db: firestore.Client) -> None:
    jira = Jira()
    repo = ActionRepository(db)
    now = datetime.now(UTC)
    repo.create_conversation("u-par", {"messageCount": 0, "createdAt": now})
    payload = create_payload(pix_story(), "ABC", ["specflow"], None)
    [cid] = [
        d.id for d in db.collection("users").document("u-par").collection("conversations").stream()
    ]
    aid = repo.create_action(
        "u-par",
        {
            "kind": "create_issue",
            "payload": payload,
            "payloadHash": payload_hash(payload),
            "readiness": {},
            "labels": ["specflow"],
            "preview": {"summary": "Pix"},
            "status": "pending",
            "conversationId": cid,
            "connectionId": "conn-1",
            "siteUrl": "https://sandbox-teste.atlassian.net",
            "createdAt": now,
            "expiresAt": now.replace(year=now.year + 1),
        },
    )
    service = ActionService(
        repo,
        cast(JiraConnectionService, FakeJiraService(handler=jira)),
        Settings(env="test", gcp_project=PROJECT, firestore_database=DATABASE),
    )

    results = await asyncio.gather(
        *(service.confirm("u-par", aid) for _ in range(10)), return_exceptions=True
    )

    kinds = [type(r).__name__ + ": " + str(r)[:200] for r in results]
    assert len(jira.writes) == 1, kinds
    assert sum(not isinstance(r, BaseException) for r in results) == 1, kinds
    assert {r.status for r in results if isinstance(r, ApiProblemError)} == {409}, kinds
