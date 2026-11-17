"""Projetos Jira (F09): cliente paginado, contagens, cache e a rota /api/v1/jira/projects."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.api.deps import get_jira_project_service, get_jira_service, get_verifier
from app.core.config import Settings, get_settings
from app.core.crypto import LocalFernetCipher
from app.integrations.jira.client import JiraClient
from app.main import create_app
from app.services.jira_connections import JiraConnectionService
from app.services.jira_projects import JiraProjectService, open_issues_jql
from tests.fakes import FakeVerifier, MemoryJiraStore, MemoryProjectCache
from tests.jira_fake import EMAIL, SITE, TOKEN, myself

ALICE = {"Authorization": "Bearer ok:alice"}
BOB = {"Authorization": "Bearer ok:bob"}
URL = "/api/v1/jira/projects"
SEARCH = f"{SITE}/rest/api/3/project/search"
COUNT = f"{SITE}/rest/api/3/search/approximate-count"


def _project(key: str, total: int | None = 7) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": f"id-{key}",
        "key": key,
        "name": f"Projeto {key}",
        "projectTypeKey": "software",
        "avatarUrls": {"48x48": f"{SITE}/rest/api/3/universal_avatar/view/type/project/avatar/1"},
    }
    if total is not None:
        data["insight"] = {"totalIssueCount": total}
    return data


def _pages(router: respx.MockRouter, keys: list[str], page_size: int = 50) -> respx.Route:
    def handler(request: httpx.Request) -> httpx.Response:
        start = int(request.url.params["startAt"])
        chunk = keys[start : start + page_size]
        return httpx.Response(
            200,
            json={
                "values": [_project(k) for k in chunk],
                "isLast": start + page_size >= len(keys),
            },
        )

    return router.get(SEARCH).mock(side_effect=handler)


def _counts(router: respx.MockRouter, open_by_key: dict[str, int]) -> respx.Route:
    def handler(request: httpx.Request) -> httpx.Response:
        jql = httpx.Request("POST", "x", content=request.content).read().decode()
        key = jql.split('project = \\"')[1].split('\\"')[0]
        if key not in open_by_key:
            return httpx.Response(500)
        return httpx.Response(200, json={"count": open_by_key[key]})

    return router.post(COUNT).mock(side_effect=handler)


# --- cliente ---------------------------------------------------------------------------------


def _client() -> JiraClient:
    async def no_sleep(_: float) -> None:
        return None

    return JiraClient(SITE, EMAIL, TOKEN, sleep=no_sleep)


@pytest.mark.req("F09-RT-03")
@respx.mock
async def test_pagina_ate_o_fim_com_insight() -> None:
    keys = [f"P{i:03d}" for i in range(120)]
    route = _pages(respx.mock, keys)
    async with _client() as jira:
        projects = await jira.list_projects(insight=True, max_pages=20)

    assert [p.key for p in projects] == keys
    assert [c.request.url.params["startAt"] for c in route.calls] == ["0", "50", "100"]
    assert route.calls.last.request.url.params["expand"] == "insight"
    first = projects[0]
    assert (first.id, first.total_issues, first.type) == ("id-P000", 7, "software")
    assert first.avatar_url
    assert first.avatar_url.startswith("https://")


@pytest.mark.req("F09-RT-03")
@respx.mock
async def test_teto_de_paginas() -> None:
    route = respx.get(SEARCH).respond(200, json={"values": [_project("A")], "isLast": False})
    async with _client() as jira:
        projects = await jira.list_projects(insight=True, max_pages=3)

    assert len(projects) == 3
    assert route.call_count == 3


@respx.mock
async def test_agente_continua_lendo_so_a_primeira_pagina() -> None:
    route = respx.get(SEARCH).respond(200, json={"values": [_project("A")], "isLast": False})
    async with _client() as jira:
        await jira.list_projects()

    assert route.call_count == 1
    assert "expand" not in route.calls.last.request.url.params


@respx.mock
async def test_avatar_que_nao_e_https_e_descartado() -> None:
    data = {**_project("A", total=None), "avatarUrls": {"48x48": "javascript:alert(1)"}}
    respx.get(SEARCH).respond(200, json={"values": [data], "isLast": True})
    async with _client() as jira:
        [project] = await jira.list_projects(insight=True)

    assert (project.avatar_url, project.total_issues) == (None, None)


@pytest.mark.req("F09-RF-02")
@respx.mock
async def test_approximate_count() -> None:
    route = respx.post(COUNT).respond(200, json={"count": 22})
    async with _client() as jira:
        assert await jira.approximate_count(open_issues_jql("ABC")) == 22

    assert route.calls.last.request.read() == (
        b'{"jql":"project = \\"ABC\\" AND statusCategory != Done"}'
    )


# --- serviço e rota --------------------------------------------------------------------------


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def cache() -> MemoryProjectCache:
    return MemoryProjectCache()


@pytest.fixture
def store() -> MemoryJiraStore:
    return MemoryJiraStore()


@pytest.fixture
def jira() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False) as router:
        myself(router)
        yield router


@pytest.fixture
def client(
    store: MemoryJiraStore, cache: MemoryProjectCache, clock: Clock, jira: respx.MockRouter
) -> Iterator[TestClient]:
    app = create_app()
    connections = JiraConnectionService(store, LocalFernetCipher())
    projects = JiraProjectService(connections, cache, clock)
    app.dependency_overrides[get_settings] = lambda: Settings(env="test")
    app.dependency_overrides[get_verifier] = FakeVerifier
    app.dependency_overrides[get_jira_service] = lambda: connections
    app.dependency_overrides[get_jira_project_service] = lambda: projects
    with TestClient(app) as c:
        yield c


def _connect(client: TestClient, headers: dict[str, str] = ALICE) -> str:
    body = {"site_url": SITE, "email": EMAIL, "api_token": TOKEN}
    response = client.post("/api/v1/jira/connections", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


@pytest.mark.req("F09-RF-01")
@pytest.mark.req("F09-RF-02")
@pytest.mark.req("F09-RF-04")
@pytest.mark.req("F09-RT-02")
def test_lista_com_contagens_e_links(client: TestClient, jira: respx.MockRouter) -> None:
    _connect(client)
    _pages(jira, ["ABC", "PAG"])
    _counts(jira, {"ABC": 3, "PAG": 0})

    response = client.get(URL, headers=ALICE)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["items"] == [
        {
            "id": "id-ABC",
            "key": "ABC",
            "name": "Projeto ABC",
            "type": "software",
            "avatar_url": f"{SITE}/rest/api/3/universal_avatar/view/type/project/avatar/1",
            "open_issues": 3,
            "total_issues": 7,
            "url": f"{SITE}/browse/ABC",
        },
        {
            "id": "id-PAG",
            "key": "PAG",
            "name": "Projeto PAG",
            "type": "software",
            "avatar_url": f"{SITE}/rest/api/3/universal_avatar/view/type/project/avatar/1",
            "open_issues": 0,
            "total_issues": 7,
            "url": f"{SITE}/browse/PAG",
        },
    ]
    assert TOKEN not in response.text


@pytest.mark.req("F09-RT-04")
def test_falha_numa_contagem_nao_quebra_a_lista(client: TestClient, jira: respx.MockRouter) -> None:
    _connect(client)
    _pages(jira, ["ABC", "PAG"])
    _counts(jira, {"ABC": 3})  # PAG responde 500

    items = client.get(URL, headers=ALICE).json()["items"]

    assert [(i["key"], i["open_issues"]) for i in items] == [("ABC", 3), ("PAG", None)]


@pytest.mark.req("F09-RT-01")
def test_contagens_com_concorrencia_maxima_5(client: TestClient, jira: respx.MockRouter) -> None:
    _connect(client)
    keys = [f"P{i}" for i in range(12)]
    _pages(jira, keys)
    state = {"now": 0, "max": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        state["now"] += 1
        state["max"] = max(state["max"], state["now"])
        await asyncio.sleep(0.01)
        state["now"] -= 1
        return httpx.Response(200, json={"count": 1})

    jira.post(COUNT).mock(side_effect=handler)

    items = client.get(URL, headers=ALICE).json()["items"]

    assert len(items) == 12
    assert 1 < state["max"] <= 5


@pytest.mark.req("F09-RT-01")
@pytest.mark.req("F09-RF-07")
def test_cache_de_5_minutos_e_refresh(
    client: TestClient, jira: respx.MockRouter, clock: Clock, cache: MemoryProjectCache
) -> None:
    _connect(client)
    search = _pages(jira, ["ABC"])
    _counts(jira, {"ABC": 3})

    client.get(URL, headers=ALICE)
    clock.now += timedelta(minutes=4)
    cached = client.get(URL, headers=ALICE)
    assert search.call_count == 1
    assert cached.json()["items"][0]["open_issues"] == 3
    assert cached.json()["fetched_at"].startswith("2026-11-17T12:00:00")
    assert "uid-alice" in cache.docs
    assert "uid-bob" not in cache.docs

    client.get(URL, headers=ALICE, params={"refresh": "true"})
    assert search.call_count == 2

    clock.now += timedelta(minutes=6)
    client.get(URL, headers=ALICE)
    assert search.call_count == 3


@pytest.mark.req("F09-RT-01")
def test_cache_de_outra_conexao_nao_vale(
    client: TestClient, jira: respx.MockRouter, cache: MemoryProjectCache
) -> None:
    connection = _connect(client)
    search = _pages(jira, ["ABC"])
    _counts(jira, {"ABC": 3})
    client.get(URL, headers=ALICE)
    cache.docs["uid-alice"]["connectionId"] = "outra"

    client.get(URL, headers=ALICE)

    assert search.call_count == 2
    assert cache.docs["uid-alice"]["connectionId"] == connection


@pytest.mark.req("F09-RF-06")
@pytest.mark.req("F09-RT-05")
def test_sem_conexao(client: TestClient) -> None:
    response = client.get(URL, headers=BOB)

    assert response.status_code == 409
    assert response.json()["code"] == "jira-not-connected"


@pytest.mark.req("F09-RF-06")
@pytest.mark.req("F09-RT-05")
def test_token_recusado_marca_a_conexao_invalida(
    client: TestClient, jira: respx.MockRouter, store: MemoryJiraStore
) -> None:
    connection = _connect(client)
    jira.get(SEARCH).respond(401)

    response = client.get(URL, headers=ALICE)

    assert response.status_code == 409
    assert response.json()["code"] == "jira-credential-rejected"
    assert store.docs["uid-alice"][connection]["status"] == "invalid"
    assert TOKEN not in response.text


@pytest.mark.req("F09-RT-05")
def test_jira_fora_do_ar(client: TestClient, jira: respx.MockRouter) -> None:
    _connect(client)
    jira.get(SEARCH).respond(503)

    response = client.get(URL, headers=ALICE)

    assert response.status_code == 502
    assert response.json()["code"] == "jira-unreachable"


def test_exige_login(client: TestClient) -> None:
    assert client.get(URL).status_code == 401
