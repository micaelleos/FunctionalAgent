"""Escritas no Jira (F06): só depois da confirmação, e nunca repetidas depois de enviadas."""

import json

import httpx
import pytest

from app.integrations.jira.client import (
    JiraAuthError,
    JiraBadRequestError,
    JiraClient,
    JiraForbiddenError,
    JiraNotFoundError,
    JiraRateLimitedError,
    JiraUncertainError,
    JiraUnreachableError,
)

pytestmark = pytest.mark.req("F06-RF-02")

SITE = "https://sandbox-teste.atlassian.net"


def _client(*replies: httpx.Response | Exception) -> tuple[JiraClient, list[httpx.Request]]:
    queue, seen = list(replies), []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        reply = queue.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    async def no_sleep(_: float) -> None:
        return None

    client = JiraClient(
        SITE, "po@teste.dev", "x" * 12, transport=httpx.MockTransport(handler), sleep=no_sleep
    )
    return client, seen


async def test_create_issue_envia_os_campos_e_devolve_chave_e_link() -> None:
    client, seen = _client(httpx.Response(201, json={"id": "10", "key": "ABC-12"}))

    created = await client.create_issue({"summary": "Título"})

    assert (created.key, created.url) == ("ABC-12", f"{SITE}/browse/ABC-12")
    [request] = seen
    assert (request.method, request.url.path) == ("POST", "/rest/api/3/issue")
    assert json.loads(request.content) == {"fields": {"summary": "Título"}}


@pytest.mark.req("F06-RF-06")
async def test_update_issue_usa_put_na_issue() -> None:
    client, seen = _client(httpx.Response(204))

    await client.update_issue("ABC-7", {"priority": {"name": "Low"}})

    [request] = seen
    assert (request.method, request.url.path) == ("PUT", "/rest/api/3/issue/ABC-7")


@pytest.mark.req("F06-RT-01")
@pytest.mark.parametrize(
    ("reply", "error"),
    [
        (httpx.Response(500), JiraUncertainError),
        (httpx.Response(503), JiraUncertainError),
        (httpx.ReadTimeout("lento"), JiraUncertainError),
        (httpx.ConnectError("fora"), JiraUnreachableError),
        (httpx.Response(401), JiraAuthError),
        (httpx.Response(403, json={"errorMessages": ["sem permissão"]}), JiraForbiddenError),
        (httpx.Response(404), JiraNotFoundError),
    ],
)
async def test_escrita_nunca_e_repetida_depois_de_enviada(
    reply: httpx.Response | Exception, error: type[Exception]
) -> None:
    client, seen = _client(reply, httpx.Response(201, json={"key": "ABC-1"}))

    with pytest.raises(error):
        await client.create_issue({"summary": "x"})
    assert len(seen) == 1


async def test_429_e_repetido_porque_o_jira_nao_processou() -> None:
    client, seen = _client(httpx.Response(429), httpx.Response(201, json={"key": "ABC-1"}))

    created = await client.create_issue({"summary": "x"})

    assert created.key == "ABC-1"
    assert len(seen) == 2


async def test_429_persistente_vira_rate_limited() -> None:
    client, _ = _client(*(httpx.Response(429) for _ in range(3)))

    with pytest.raises(JiraRateLimitedError):
        await client.create_issue({"summary": "x"})


@pytest.mark.req("F06-RF-07")
async def test_400_traz_os_erros_por_campo() -> None:
    body = {"errorMessages": [], "errors": {"priority": "Priority name 'X' is not valid"}}
    client, _ = _client(httpx.Response(400, json=body))

    with pytest.raises(JiraBadRequestError) as info:
        await client.create_issue({"summary": "x"})

    assert info.value.errors == {"priority": "Priority name 'X' is not valid"}
    assert str(info.value) == "priority: Priority name 'X' is not valid"


async def test_tipos_do_projeto_com_os_nomes_do_site() -> None:
    types = [
        {"id": "10004", "name": "História", "hierarchyLevel": 0, "subtask": False},
        {"id": "10002", "name": "Subtarefa", "hierarchyLevel": -1, "subtask": True},
    ]
    client, seen = _client(httpx.Response(200, json={"issueTypes": types}))

    found = await client.project_issue_types("SCRUM")

    assert [(t.id, t.name, t.hierarchy_level, t.subtask) for t in found] == [
        ("10004", "História", 0, False),
        ("10002", "Subtarefa", -1, True),
    ]
    assert seen[0].url.path == "/rest/api/3/issue/createmeta/SCRUM/issuetypes"
