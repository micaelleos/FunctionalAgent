"""Conexão Jira com Firestore e Auth dos emuladores (F04-RT-01, F04-RT-02, Constituição II)."""

from collections.abc import Iterator

import pytest
import respx
from fastapi.testclient import TestClient
from google.cloud import firestore

from tests.integration.conftest import AuthEmulator
from tests.jira_fake import EMAIL, SITE, TOKEN, myself

BASE = "/api/v1/jira/connections"
BODY = {"site_url": SITE, "email": EMAIL, "api_token": TOKEN}


@pytest.fixture(autouse=True)
def jira() -> Iterator[respx.MockRouter]:
    # Só o Jira é simulado; Auth e Firestore (emuladores, via HTTP/gRPC locais) passam direto.
    with respx.mock(assert_all_called=False) as router:
        router.route(host__regex=r"^(localhost|127\.0\.0\.1|emulators|0\.0\.0\.0)$").pass_through()
        myself(router)
        yield router


@pytest.mark.req("F04-RT-01")
@pytest.mark.req("F04-RT-02")
def test_documento_cru_tem_so_ciphertext(
    client: TestClient, auth_emulator: AuthEmulator, db: firestore.Client
) -> None:
    alice = auth_emulator.create_user()

    created = client.post(BASE, json=BODY, headers=alice.headers)

    assert created.status_code == 201, created.text
    raw = (
        db.collection("users")
        .document(alice.uid)
        .collection("jira_connections")
        .document(created.json()["id"])
        .get()
        .to_dict()
    )
    assert raw is not None
    assert isinstance(raw["tokenCiphertext"], bytes)
    assert TOKEN.encode() not in raw["tokenCiphertext"]
    assert raw["kmsKeyVersion"]
    assert TOKEN not in str({k: v for k, v in raw.items() if k != "tokenCiphertext"})


@pytest.mark.req("F04-RT-02")
def test_exportacao_e_exclusao_da_conta(
    client: TestClient, auth_emulator: AuthEmulator, db: firestore.Client
) -> None:
    alice = auth_emulator.create_user()
    client.get("/api/v1/me", headers=alice.headers)
    client.post(BASE, json=BODY, headers=alice.headers)

    exported = client.get("/api/v1/me/export", headers=alice.headers)

    assert exported.status_code == 200
    connection = exported.json()["user"]["collections"]["jira_connections"][0]["data"]
    assert connection["siteUrl"] == SITE
    assert "tokenCiphertext" not in connection
    assert TOKEN not in exported.text

    assert client.delete("/api/v1/me", headers=alice.headers).status_code == 204
    left = db.collection("users").document(alice.uid).collection("jira_connections").get()
    assert list(left) == []


def test_isolamento_entre_usuarios(client: TestClient, auth_emulator: AuthEmulator) -> None:
    alice = auth_emulator.create_user()
    bob = auth_emulator.create_user()
    created = client.post(BASE, json=BODY, headers=alice.headers).json()

    assert client.get(BASE, headers=bob.headers).json() == []
    assert client.post(f"{BASE}/{created['id']}/validate", headers=bob.headers).status_code == 404


@pytest.mark.req("F04-RF-05")
def test_trocar_e_remover_no_firestore(
    client: TestClient, auth_emulator: AuthEmulator, jira: respx.MockRouter
) -> None:
    alice = auth_emulator.create_user()
    created = client.post(BASE, json=BODY, headers=alice.headers).json()
    novo = "ATATT-outro-token-7777"
    myself(jira, valid_token=novo)

    replaced = client.put(
        f"{BASE}/{created['id']}", json={**BODY, "api_token": novo}, headers=alice.headers
    )

    assert replaced.json()["token_hint"] == "7777"
    assert client.get(BASE, headers=alice.headers).json()[0]["token_hint"] == "7777"
    assert client.delete(f"{BASE}/{created['id']}", headers=alice.headers).status_code == 204
    assert client.get(BASE, headers=alice.headers).json() == []
