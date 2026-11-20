"""Vínculo projeto ↔ espaço e rotas do Confluence (F19-RF-01, F19-RF-02, F19-RF-09, F19-RT-07,
F19-RT-08)."""

from collections.abc import Iterator
from datetime import UTC, datetime

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.api.deps import get_confluence_link_service, get_jira_service, get_verifier
from app.core.config import Settings, get_settings
from app.core.crypto import LocalFernetCipher
from app.main import create_app
from app.services.confluence_links import ConfluenceLinkService
from app.services.jira_connections import JiraConnectionService
from tests.confluence_fake import SPACE, WIKI, search_json, spaces
from tests.fakes import FakeVerifier, MemoryJiraStore, MemoryLinkStore
from tests.jira_fake import EMAIL, SITE, TOKEN, myself

ALICE = {"Authorization": "Bearer ok:alice"}
BOB = {"Authorization": "Bearer ok:bob"}
NOW = datetime(2026, 11, 20, 12, tzinfo=UTC)
DOCS = {**SPACE, "id": "777", "key": "DOCS", "name": "Loja — Documentação"}


@pytest.fixture
def links() -> MemoryLinkStore:
    return MemoryLinkStore()


@pytest.fixture
def atlassian() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False) as router:
        myself(router)
        yield router


@pytest.fixture
def client(links: MemoryLinkStore, atlassian: respx.MockRouter) -> Iterator[TestClient]:
    app = create_app()
    connections = JiraConnectionService(MemoryJiraStore(), LocalFernetCipher())
    service = ConfluenceLinkService(links, connections, clock=lambda: NOW)
    app.dependency_overrides[get_settings] = lambda: Settings(env="test")
    app.dependency_overrides[get_verifier] = FakeVerifier
    app.dependency_overrides[get_jira_service] = lambda: connections
    app.dependency_overrides[get_confluence_link_service] = lambda: service
    with TestClient(app) as c:
        yield c


def _connect(client: TestClient, headers: dict[str, str] = ALICE) -> None:
    body = {"site_url": SITE, "email": EMAIL, "api_token": TOKEN}
    assert client.post("/api/v1/jira/connections", json=body, headers=headers).status_code == 201


def _no_label(router: respx.MockRouter) -> None:
    router.get(f"{WIKI}/rest/api/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )


@pytest.mark.req("F19-RF-01")
def test_sugere_espaco_com_a_mesma_chave_sem_salvar(
    client: TestClient, atlassian: respx.MockRouter, links: MemoryLinkStore
) -> None:
    _connect(client)
    spaces(atlassian, SPACE)

    out = client.get("/api/v1/jira/projects/SCRUM/confluence", headers=ALICE)

    assert out.status_code == 200, out.text
    assert out.json() == {
        "link": None,
        "suggestion": {
            "space": {"key": "SCRUM", "name": "Minha equipe", "url": f"{WIKI}/spaces/SCRUM"},
            "source": "same-key",
        },
        "available": True,
    }
    assert links.docs == {}  # a descoberta só sugere (Constituição IV)


@pytest.mark.req("F19-RF-01")
def test_sugere_pelo_rotulo_do_projeto(client: TestClient, atlassian: respx.MockRouter) -> None:
    _connect(client)
    spaces(atlassian)  # nenhum espaço com a chave
    search = atlassian.get(f"{WIKI}/rest/api/search").mock(
        return_value=httpx.Response(200, json=search_json(("55", "Início", ["specflow"])))
    )
    atlassian.get(f"{WIKI}/api/v2/pages/55").mock(
        return_value=httpx.Response(200, json={"id": "55", "spaceId": "777"})
    )
    atlassian.get(f"{WIKI}/api/v2/spaces/777").mock(return_value=httpx.Response(200, json=DOCS))

    out = client.get("/api/v1/jira/projects/ABC/confluence", headers=ALICE).json()

    assert out["suggestion"]["source"] == "label"
    assert out["suggestion"]["space"]["key"] == "DOCS"
    assert 'label = "specflow-projeto-abc"' in search.calls.last.request.url.params["cql"]


@pytest.mark.req("F19-RF-02")
@pytest.mark.req("F19-RT-07")
def test_vincula_troca_e_desvincula_por_usuario(
    client: TestClient, atlassian: respx.MockRouter, links: MemoryLinkStore
) -> None:
    _connect(client)
    _connect(client, BOB)
    spaces(atlassian, SPACE, DOCS)
    _no_label(atlassian)
    url = "/api/v1/jira/projects/SCRUM/confluence"

    first = client.put(url, json={"space_key": "SCRUM"}, headers=ALICE)
    assert first.status_code == 200, first.text
    assert first.json()["source"] == "same-key"
    swapped = client.put(url, json={"space_key": "DOCS"}, headers=ALICE).json()
    assert swapped["source"] == "manual"

    doc = links.docs[("uid-alice", "SCRUM")]
    assert {k: doc[k] for k in ("spaceId", "spaceKey", "source")} == {
        "spaceId": "777",
        "spaceKey": "DOCS",
        "source": "manual",
    }
    assert set(doc) == {
        "connectionId",
        "spaceId",
        "spaceKey",
        "spaceName",
        "spaceUrl",
        "source",
        "linkedAt",
    }
    assert client.get(url, headers=ALICE).json()["link"]["space"]["key"] == "DOCS"
    assert client.get(url, headers=BOB).json()["link"] is None

    assert client.delete(url, headers=ALICE).status_code == 204
    assert ("uid-alice", "SCRUM") not in links.docs


@pytest.mark.req("F19-RF-02")
def test_espaco_inexistente_nao_vincula(
    client: TestClient, atlassian: respx.MockRouter, links: MemoryLinkStore
) -> None:
    _connect(client)
    spaces(atlassian, SPACE)
    _no_label(atlassian)
    out = client.put(
        "/api/v1/jira/projects/SCRUM/confluence", json={"space_key": "NADA"}, headers=ALICE
    )
    assert out.status_code == 404
    assert out.json()["type"].endswith("confluence-space-not-found")
    assert links.docs == {}


@pytest.mark.req("F19-RF-09")
def test_sem_acesso_ao_confluence_nao_invalida_o_jira(
    client: TestClient, atlassian: respx.MockRouter
) -> None:
    _connect(client)
    atlassian.get(f"{WIKI}/api/v2/spaces").mock(return_value=httpx.Response(403))

    found = client.get("/api/v1/jira/projects/SCRUM/confluence", headers=ALICE)
    linked = client.put(
        "/api/v1/jira/projects/SCRUM/confluence", json={"space_key": "SCRUM"}, headers=ALICE
    )
    listed = client.get("/api/v1/confluence/spaces", headers=ALICE)

    assert found.json()["available"] is False
    assert linked.status_code == 403
    assert linked.json()["type"].endswith("confluence-forbidden")
    assert listed.status_code == 403
    [connection] = client.get("/api/v1/jira/connections", headers=ALICE).json()
    assert connection["status"] == "ok"


@pytest.mark.req("F19-RT-08")
def test_lista_espacos_filtrando(client: TestClient, atlassian: respx.MockRouter) -> None:
    _connect(client)
    spaces(atlassian, SPACE, DOCS)
    out = client.get("/api/v1/confluence/spaces", params={"q": "docs"}, headers=ALICE)
    assert [s["key"] for s in out.json()] == ["DOCS"]


@pytest.mark.req("F19-RT-08")
def test_sem_jira_conectado_e_chave_invalida(client: TestClient) -> None:
    out = client.get("/api/v1/jira/projects/SCRUM/confluence", headers=ALICE)
    assert out.status_code == 409
    assert out.json()["type"].endswith("jira-not-connected")
    bad = client.get("/api/v1/jira/projects/a%2Fb/confluence", headers=ALICE)
    assert bad.status_code in (404, 422)
