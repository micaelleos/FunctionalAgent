"""Vínculo projeto ↔ espaço no Firestore do emulador (F19-RT-07, Constituição II)."""

from collections.abc import Iterator

import pytest
import respx
from fastapi.testclient import TestClient
from google.cloud import firestore

from tests.confluence_fake import SPACE, WIKI, spaces
from tests.integration.conftest import AuthEmulator
from tests.jira_fake import EMAIL, SITE, TOKEN, myself


@pytest.fixture(autouse=True)
def atlassian() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False) as router:
        router.route(host__regex=r"^(localhost|127\.0\.0\.1|emulators|0\.0\.0\.0)$").pass_through()
        myself(router)
        spaces(router, SPACE)
        router.get(f"{WIKI}/rest/api/search").respond(200, json={"results": []})
        yield router


@pytest.mark.req("F19-RT-07")
def test_vinculo_guarda_so_o_espaco_e_sai_com_a_conta(
    client: TestClient, auth_emulator: AuthEmulator, db: firestore.Client
) -> None:
    alice = auth_emulator.create_user()
    body = {"site_url": SITE, "email": EMAIL, "api_token": TOKEN}
    created = client.post("/api/v1/jira/connections", json=body, headers=alice.headers)
    assert created.status_code == 201

    url = "/api/v1/jira/projects/SCRUM/confluence"
    linked = client.put(url, json={"space_key": "SCRUM"}, headers=alice.headers)
    assert linked.status_code == 200, linked.text

    ref = db.collection("users").document(alice.uid).collection("project_links").document("SCRUM")
    raw = ref.get().to_dict() or {}
    assert raw["spaceKey"] == "SCRUM"
    assert raw["spaceId"] == "65801"
    assert not {"content", "body", "markdown"} & set(raw)

    assert client.delete(url, headers=alice.headers).status_code == 204
    assert not ref.get().exists
