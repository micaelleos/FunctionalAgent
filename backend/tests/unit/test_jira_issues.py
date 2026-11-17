"""Histórico de issues (F10): registro com a ação, filtros, status e "Copiar para agente"."""

import json
from datetime import timedelta
from typing import Any, cast

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent.spec.jira_payload import create_payload, update_payload
from app.api.deps import get_jira_issue_service, get_verifier
from app.core.config import Settings, get_settings
from app.core.errors import ApiProblemError
from app.main import create_app
from app.services.actions import ActionService
from app.services.chat import ACTION_TTL
from app.services.conversations import ConversationService
from app.services.jira_connections import JiraConnectionService
from app.services.jira_issues import JiraIssueService
from tests.chat_fakes import NOW, SITE, FakeJiraService, MemoryChatStore
from tests.fakes import FakeVerifier
from tests.spec_fixtures import pix_story
from tests.unit.test_actions import FakeJira, _propose

UID = "uid-alice"  # o FakeVerifier troca "ok:alice" por "uid-alice"
ALICE = {"Authorization": "Bearer ok:alice"}
URL = "/api/v1/jira/issues"


class Env:
    def __init__(self, status_handler: Any = None) -> None:
        self.store = MemoryChatStore()
        self.jira = FakeJira()
        self.now = NOW
        self.store.conversations[UID] = {
            "conv-1": {"messageCount": 2, "title": "Checkout Pix"},
            "conv-2": {"messageCount": 0, "title": "Login"},
        }
        writes = FakeJiraService(handler=self.jira)
        self.actions = ActionService(
            self.store,
            cast(JiraConnectionService, writes),
            Settings(env="test"),
            clock=lambda: self.now,
        )
        self.reads = FakeJiraService(handler=status_handler or (lambda r: httpx.Response(500)))
        self.service = JiraIssueService(self.store, cast(JiraConnectionService, self.reads))

    async def create(
        self, project: str = "ABC", labels: list[str] | None = None, conv: str = "conv-1"
    ) -> str:
        payload = create_payload(pix_story(), project, labels or ["agent-ready", "specflow"], None)
        aid = _propose(
            self.store,
            payload,
            uid=UID,
            conversationId=conv,
            createdAt=self.now,
            expiresAt=self.now + ACTION_TTL,
        )
        out = await self.actions.confirm(UID, aid)
        self.now += timedelta(minutes=1)
        assert out.result is not None
        return out.result.issue_key


@pytest.mark.req("F10-RT-01")
@pytest.mark.req("F10-RF-02")
async def test_criacao_e_atualizacao_entram_no_historico() -> None:
    env = Env()
    key = await env.create()
    created_at = env.store.issues[UID][key]["createdAt"]

    payload = update_payload(key, None, "Low", ["specflow", "time-a"])
    aid = _propose(env.store, payload, kind="update_issue", uid=UID)
    await env.actions.confirm(UID, aid)

    record = env.store.issues[UID][key]
    assert record["operation"] == "created"
    assert record["createdAt"] == created_at  # a atualização não muda a 1ª gravação
    assert record["updatedAt"] == env.now
    assert record["labels"] == ["specflow", "time-a"]
    assert record["lastActionId"] == aid
    action = env.store.get_action(UID, aid)
    assert action is not None
    assert action["status"] == "done"  # mesma transação


@pytest.mark.req("F10-RF-01")
@pytest.mark.req("F10-RF-04")
@pytest.mark.req("F10-RF-07")
async def test_lista_do_mais_recente_com_conversa_e_prontidao() -> None:
    env = Env()
    first = await env.create(labels=["agent-ready", "specflow"])
    second = await env.create(labels=["human-only", "specflow"], conv="conv-2")
    third = await env.create(labels=["specflow"])

    page = await env.service.issues(UID)

    assert [i.key for i in page.items] == [third, second, first]
    by_key = {i.key: i for i in page.items}
    assert by_key[first].readiness == "agent_ready"
    assert by_key[second].readiness == "human_only"
    assert by_key[third].readiness == "not_ready"
    assert (by_key[second].conversation_id, by_key[second].conversation_title) == (
        "conv-2",
        "Login",
    )
    assert by_key[first].url == f"{SITE}/browse/{first}"
    assert by_key[first].has_spec
    assert page.next_cursor is None


@pytest.mark.req("F10-RF-03")
async def test_filtros_e_cursor() -> None:
    env = Env()
    keys = [await env.create(project=p) for p in ["ABC", "XYZ", "ABC", "ABC", "XYZ"]]
    abc = [k for k, p in zip(keys, ["ABC", "XYZ", "ABC", "ABC", "XYZ"], strict=True) if p == "ABC"]

    page1 = await env.service.issues(UID, project="ABC", limit=2)
    page2 = await env.service.issues(UID, project="ABC", limit=2, cursor=page1.next_cursor)

    assert [i.key for i in page1.items + page2.items] == list(reversed(abc))
    assert page2.next_cursor is None
    assert (await env.service.issues(UID, issue_type="Epic")).items == []
    assert len((await env.service.issues(UID, issue_type="Story")).items) == 5
    assert (await env.service.issues(UID, readiness="human_only")).items == []


@pytest.mark.req("F10-RF-03")
async def test_periodo() -> None:
    env = Env()
    start = env.now
    old = await env.create()
    env.now += timedelta(days=3)
    new = await env.create()

    recent = await env.service.issues(UID, since=start + timedelta(days=1))
    older = await env.service.issues(UID, until=start + timedelta(days=1))

    assert [i.key for i in recent.items] == [new]
    assert [i.key for i in older.items] == [old]


@pytest.mark.req("F10-RT-03")
async def test_conversa_excluida_fica_sem_vinculo() -> None:
    env = Env()
    key = await env.create()

    await ConversationService(env.store).delete(UID, "conv-1")

    [item] = (await env.service.issues(UID)).items
    assert item.key == key
    assert (item.conversation_id, item.conversation_title) == (None, None)


@pytest.mark.req("F10-RT-03")
async def test_conversa_apagada_antes_da_f10_tambem_some_o_link() -> None:
    env = Env()
    await env.create()
    env.store.conversations[UID].pop("conv-1")  # vínculo antigo, sem a limpeza

    [item] = (await env.service.issues(UID)).items
    assert item.conversation_id is None


@pytest.mark.req("F10-RF-06")
async def test_copiar_para_agente_usa_a_spec_confirmada() -> None:
    env = Env()
    key = await env.create()

    prompt = await env.service.agent_prompt(UID, key)

    assert prompt.text.startswith(f"Implemente a issue {key} abaixo.")
    assert f"# {key} · {pix_story().title}" in prompt.text
    assert f"Issue no Jira: {SITE}/browse/{key}" in prompt.text
    assert "## Critérios de aceite" in prompt.text


@pytest.mark.req("F10-RF-06")
async def test_atualizacao_com_spec_nova_vira_a_base_do_copiar() -> None:
    env = Env()
    key = await env.create()
    changed = pix_story().model_copy(update={"title": "Pagar com Pix e cartão"})
    aid = _propose(
        env.store, update_payload(key, changed, None, None), kind="update_issue", uid=UID
    )
    await env.actions.confirm(UID, aid)

    prompt = await env.service.agent_prompt(UID, key)

    assert f"# {key} · Pagar com Pix e cartão" in prompt.text


@pytest.mark.req("F10-RF-06")
async def test_so_atualizacao_sem_spec_nao_tem_o_que_copiar() -> None:
    env = Env()
    aid = _propose(
        env.store, update_payload("OLD-3", None, "Low", None), kind="update_issue", uid=UID
    )
    await env.actions.confirm(UID, aid)

    [item] = (await env.service.issues(UID)).items
    assert (item.key, item.operation, item.has_spec, item.project_key) == (
        "OLD-3",
        "updated",
        False,
        "OLD",
    )
    with pytest.raises(ApiProblemError) as exc:
        await env.service.agent_prompt(UID, "OLD-3")
    assert exc.value.code == "spec-unavailable"


def _bulk(found: dict[str, tuple[str, str]]) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/api/3/issue/bulkfetch"
        keys = json.loads(request.content)["issueIdsOrKeys"]
        issues = [
            {
                "key": k,
                "fields": {"status": {"name": found[k][0], "statusCategory": {"key": found[k][1]}}},
            }
            for k in keys
            if k in found
        ]
        return httpx.Response(200, json={"issues": issues, "issueErrors": []})

    return handler


@pytest.mark.req("F10-RF-05")
@pytest.mark.req("F10-RT-05")
async def test_status_numa_chamada_e_issue_apagada_vira_none() -> None:
    env = Env(_bulk({"ABC-1": ("A fazer", "new"), "ABC-2": ("Concluído", "done")}))

    out = await env.service.statuses(UID, ["ABC-1", "abc-2", "ABC-9", "ABC-1"])

    assert len(env.reads.requests) == 1
    assert out.model_dump()["statuses"] == {
        "ABC-1": {"name": "A fazer", "category": "new"},
        "ABC-2": {"name": "Concluído", "category": "done"},
        "ABC-9": None,
    }


@pytest.mark.req("F10-RT-05")
async def test_status_com_token_recusado_marca_a_conexao() -> None:
    env = Env(lambda r: httpx.Response(401))

    with pytest.raises(ApiProblemError) as exc:
        await env.service.statuses(UID, ["ABC-1"])

    assert exc.value.code == "jira-credential-rejected"
    assert env.reads.invalidated == ["conn-1"]


@pytest.mark.req("F10-RT-05")
async def test_status_limite_de_chaves() -> None:
    env = Env()
    with pytest.raises(ApiProblemError) as exc:
        await env.service.statuses(UID, [f"ABC-{i}" for i in range(51)])
    assert exc.value.code == "too-many-keys"


# --- rotas ----------------------------------------------------------------------------------


def _client(env: Env) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(env="test")
    app.dependency_overrides[get_verifier] = FakeVerifier
    app.dependency_overrides[get_jira_issue_service] = lambda: env.service
    return TestClient(app)


@pytest.mark.req("F10-RF-01")
@pytest.mark.req("F10-RF-03")
async def test_rotas() -> None:
    env = Env(_bulk({"ABC-1": ("To Do", "new")}))
    key = await env.create()
    with _client(env) as client:
        listed = client.get(URL, headers=ALICE, params={"project": "ABC", "type": "Story"})
        statuses = client.post(f"{URL}/status", headers=ALICE, json={"keys": [key]})
        prompt = client.get(f"{URL}/{key}/agent-prompt", headers=ALICE)
        missing = client.get(f"{URL}/NOPE-1/agent-prompt", headers=ALICE)
        bad = client.get(URL, headers=ALICE, params={"cursor": "%%%"})
        anonymous = client.get(URL)

    assert listed.status_code == 200
    [item] = listed.json()["items"]
    assert (item["key"], item["readiness"], item["conversation_title"]) == (
        key,
        "agent_ready",
        "Checkout Pix",
    )
    assert statuses.json() == {"statuses": {key: {"name": "To Do", "category": "new"}}}
    assert "## Critérios de aceite" in prompt.json()["text"]
    assert (missing.status_code, missing.json()["code"]) == (404, "issue-not-found")
    assert (bad.status_code, bad.json()["code"]) == (400, "invalid-cursor")
    assert anonymous.status_code == 401
