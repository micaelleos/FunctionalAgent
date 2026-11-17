"""F09-RT-06: p95 de GET /api/v1/jira/projects < 1,5 s com um Jira falso de 150 ms por chamada.

20 projetos, cache frio: 1 página + 20 contagens com concorrência 5 (5 rodadas de 150 ms).
Com o cache de 5 min, as leituras seguintes não chamam o Jira. 20 requisições, 1 a cada 5 com
`refresh`.
"""

import asyncio
import statistics
import time
from collections.abc import Iterator

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.api.deps import get_jira_project_service, get_jira_service, get_verifier
from app.core.config import Settings, get_settings
from app.core.crypto import LocalFernetCipher
from app.main import create_app
from app.services.jira_connections import JiraConnectionService
from app.services.jira_projects import JiraProjectService
from tests.fakes import FakeVerifier, MemoryJiraStore, MemoryProjectCache
from tests.jira_fake import EMAIL, SITE, TOKEN, myself

LATENCY = 0.15
ALICE = {"Authorization": "Bearer ok:alice"}


@pytest.fixture
def client() -> Iterator[TestClient]:
    async def search(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(LATENCY)
        values = [{"id": str(i), "key": f"P{i}", "name": f"P{i}"} for i in range(20)]
        return httpx.Response(200, json={"values": values, "isLast": True})

    async def count(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(LATENCY)
        return httpx.Response(200, json={"count": 1})

    with respx.mock(assert_all_called=False) as router:
        myself(router)
        router.get(f"{SITE}/rest/api/3/project/search").mock(side_effect=search)
        router.post(f"{SITE}/rest/api/3/search/approximate-count").mock(side_effect=count)
        app = create_app()
        connections = JiraConnectionService(MemoryJiraStore(), LocalFernetCipher())
        service = JiraProjectService(connections, MemoryProjectCache())
        app.dependency_overrides[get_settings] = lambda: Settings(env="test")
        app.dependency_overrides[get_verifier] = FakeVerifier
        app.dependency_overrides[get_jira_service] = lambda: connections
        app.dependency_overrides[get_jira_project_service] = lambda: service
        with TestClient(app) as c:
            body = {"site_url": SITE, "email": EMAIL, "api_token": TOKEN}
            assert c.post("/api/v1/jira/connections", json=body, headers=ALICE).status_code == 201
            yield c


@pytest.mark.req("F09-RT-06")
def test_p95_abaixo_de_1_5_s(client: TestClient) -> None:
    durations = []
    for i in range(20):
        params = {"refresh": "true"} if i % 5 == 0 else {}
        start = time.perf_counter()
        response = client.get("/api/v1/jira/projects", headers=ALICE, params=params)
        durations.append(time.perf_counter() - start)
        assert response.status_code == 200

    p95 = statistics.quantiles(durations, n=20)[-1]
    cold = max(durations[::5])
    assert cold < 1.5, durations
    assert p95 < 1.5, durations
