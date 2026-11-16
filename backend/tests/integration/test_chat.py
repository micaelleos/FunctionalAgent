"""Chat com Firestore e Auth dos emuladores e LLM roteirizado (F05-RF-02, RT-01, RT-10; T005)."""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from google.cloud import firestore
from langchain_core.messages import AIMessage

from app.agent.fake_llm import ScriptedChatModel
from app.api import deps
from tests.chat_fakes import call
from tests.integration.conftest import AuthEmulator
from tests.spec_fixtures import pix_story_data


@pytest.fixture
def llm(monkeypatch: pytest.MonkeyPatch) -> ScriptedChatModel:
    model = ScriptedChatModel(responses=[])
    monkeypatch.setattr(deps, "_chat_model", lambda settings: model)
    return model


def _events(text: str) -> list[dict[str, Any]]:
    out, current = [], {}
    for line in text.splitlines():
        if line.startswith("event: "):
            current["event"] = line[7:]
        elif line.startswith("data: "):
            current["data"] = json.loads(line[6:])
        elif not line and current:
            out.append(current)
            current = {}
    return out


def _send(client: TestClient, headers: dict[str, str], text: str, cid: str = "new") -> Any:
    return client.post(
        f"/api/v1/conversations/{cid}/messages", json={"content": text}, headers=headers
    )


@pytest.mark.req("F05-RF-02")
@pytest.mark.req("F05-RT-10")
def test_mensagens_conversa_e_uso_persistidos_por_usuario(
    client: TestClient, auth_emulator: AuthEmulator, db: firestore.Client, llm: ScriptedChatModel
) -> None:
    alice = auth_emulator.create_user()
    llm.responses += [AIMessage("Anotado."), AIMessage("Zeta.")]

    first = _send(client, alice.headers, "Meu produto se chama Zeta")
    cid = first.headers["x-conversation-id"]
    second = _send(client, alice.headers, "Qual o nome?", cid)

    assert [e["event"] for e in _events(second.text)][-2:] == ["message_saved", "done"]
    user = db.collection("users").document(alice.uid)
    conv = user.collection("conversations").document(cid).get().to_dict() or {}
    assert conv["messageCount"] == 4
    messages = [
        d.to_dict() or {}
        for d in user.collection("conversations").document(cid).collection("messages").stream()
    ]
    assert sorted((m["seq"], m["role"]) for m in messages) == [
        (1, "user"),
        (2, "assistant"),
        (3, "user"),
        (4, "assistant"),
    ]
    assert [str(m.content) for m in llm.calls[1][1:]] == [
        "Meu produto se chama Zeta",
        "Anotado.",
        "Qual o nome?",
    ]
    day = next(iter(user.collection("usage").stream())).to_dict() or {}
    assert day["messages"] == 2
    assert day["inputTokens"] == 200


@pytest.mark.req("F05-RT-01")
def test_outro_usuario_nao_continua_a_conversa(
    client: TestClient, auth_emulator: AuthEmulator, llm: ScriptedChatModel
) -> None:
    alice, bob = auth_emulator.create_user(), auth_emulator.create_user()
    llm.responses.append(AIMessage("oi"))
    cid = _send(client, alice.headers, "oi").headers["x-conversation-id"]

    response = _send(client, bob.headers, "posso ler?", cid)
    assert response.status_code == 404


@pytest.mark.req("F05-RF-08")
def test_acao_proposta_sem_jira_nao_e_gravada(
    client: TestClient, auth_emulator: AuthEmulator, db: firestore.Client, llm: ScriptedChatModel
) -> None:
    alice = auth_emulator.create_user()
    llm.responses += [
        call("propor_criacao_issue", {"project_key": "ABC", "spec": pix_story_data()}),
        AIMessage("Conecte o Jira em Configurações."),
    ]
    events = _events(_send(client, alice.headers, "Crie no ABC").text)

    assert "action_proposed" not in [e["event"] for e in events]
    actions = db.collection("users").document(alice.uid).collection("pending_actions")
    assert list(actions.stream()) == []
