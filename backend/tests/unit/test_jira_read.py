"""Leitura do Jira no cliente e no adaptador do agente (F05-RF-03, F05-RT-04)."""

import json

import httpx
import pytest
import respx

from app.agent.tools.context import IssueNotFoundError, JiraToolError
from app.integrations.jira.client import JiraBadRequestError, JiraClient, JiraNotFoundError
from app.services.jira_reader import AUTH_MESSAGE, JiraReaderAdapter
from tests.jira_fake import EMAIL, SITE, TOKEN

pytestmark = pytest.mark.req("F05-RF-03")

ISSUE = {
    "key": "ABC-1",
    "fields": {
        "summary": "Permitir login",
        "issuetype": {"name": "Story"},
        "status": {"name": "To Do"},
        "priority": {"name": "High"},
        "labels": ["specflow"],
        "parent": {"key": "ABC-0"},
        "description": {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Oi"}]}],
        },
    },
}


async def _no_sleep(_: float) -> None:
    return None


def _client() -> JiraClient:
    return JiraClient(SITE, EMAIL, TOKEN, sleep=_no_sleep)


@respx.mock
async def test_lista_projetos() -> None:
    route = respx.get(f"{SITE}/rest/api/3/project/search").respond(
        200, json={"values": [{"key": "ABC", "name": "Loja", "projectTypeKey": "software"}]}
    )
    async with _client() as jira:
        projects = await jira.list_projects()

    assert [(p.key, p.name) for p in projects] == [("ABC", "Loja")]
    assert route.calls.last.request.url.params["maxResults"] == "50"


@respx.mock
async def test_consulta_issue_com_campos_selecionados() -> None:
    route = respx.get(f"{SITE}/rest/api/3/issue/ABC-1").respond(200, json=ISSUE)
    async with _client() as jira:
        found = await jira.get_issue("ABC-1")

    assert (found.summary, found.issue_type, found.parent_key) == (
        "Permitir login",
        "Story",
        "ABC-0",
    )
    assert found.url == f"{SITE}/browse/ABC-1"
    assert "description" in route.calls.last.request.url.params["fields"]


@respx.mock
async def test_issue_inexistente_vira_not_found() -> None:
    respx.get(f"{SITE}/rest/api/3/issue/ABC-9").respond(404, json={})
    async with _client() as jira:
        with pytest.raises(JiraNotFoundError):
            await jira.get_issue("ABC-9")


@pytest.mark.req("F05-RT-04")
@respx.mock
async def test_busca_jql_limita_a_50_resultados() -> None:
    route = respx.post(f"{SITE}/rest/api/3/search/jql").respond(200, json={"issues": [ISSUE]})
    async with _client() as jira:
        found = await jira.search("project = ABC", limit=500)

    body = json.loads(route.calls.last.request.content)
    assert body["maxResults"] == 50
    assert body["jql"] == "project = ABC"
    assert [i.key for i in found] == ["ABC-1"]


@respx.mock
async def test_jql_invalida_devolve_a_mensagem_do_jira() -> None:
    respx.post(f"{SITE}/rest/api/3/search/jql").respond(
        400, json={"errorMessages": ["Campo 'statuz' não existe."]}
    )
    async with _client() as jira:
        with pytest.raises(JiraBadRequestError, match="statuz"):
            await jira.search("statuz = 1")


@respx.mock
async def test_adaptador_converte_descricao_e_erros() -> None:
    respx.get(f"{SITE}/rest/api/3/issue/ABC-1").respond(200, json=ISSUE)
    respx.get(f"{SITE}/rest/api/3/issue/ABC-9").respond(404, json={})
    respx.post(f"{SITE}/rest/api/3/search/jql").respond(503, json={})
    calls: list[str] = []

    async def invalid() -> None:
        calls.append("invalid")

    reader = JiraReaderAdapter(_client(), invalid)

    assert (await reader.get_issue("ABC-1")).description_markdown == "Oi"
    with pytest.raises(IssueNotFoundError):
        await reader.get_issue("ABC-9")
    with pytest.raises(JiraToolError, match="não respondeu"):
        await reader.search("project = ABC", 10)
    assert calls == []


@respx.mock
async def test_token_recusado_marca_a_conexao_invalida_uma_vez() -> None:
    respx.get(f"{SITE}/rest/api/3/project/search").mock(return_value=httpx.Response(401))
    calls: list[str] = []

    async def invalid() -> None:
        calls.append("invalid")

    reader = JiraReaderAdapter(_client(), invalid)
    for _ in range(2):
        with pytest.raises(JiraToolError) as exc:
            await reader.list_projects()
        assert str(exc.value) == AUTH_MESSAGE
    assert calls == ["invalid"]
