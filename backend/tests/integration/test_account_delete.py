"""Exclusão dos dados do SpecFlow AI (F03-RF-08, F03-RT-04)."""

import time

import httpx
import pytest
from fastapi.testclient import TestClient
from google.cloud import firestore

from tests.integration.conftest import AUTH_HOST, PROJECT, AuthEmulator


@pytest.mark.req("F03-RF-08")
def test_exclusao_apaga_dados_e_mantem_o_login(
    client: TestClient, auth_emulator: AuthEmulator, db: firestore.Client
) -> None:
    alice = auth_emulator.create_user(name="Alice")
    client.get("/api/v1/me", headers=alice.headers)
    ref = db.collection("users").document(alice.uid)
    ref.collection("conversations").document("c1").set({"title": "x"})

    assert client.delete("/api/v1/me", headers=alice.headers).status_code == 204
    assert not ref.get().exists
    assert not list(ref.collection("conversations").stream())

    # O login é do Auth compartilhado do portfólio: continua existindo (F03-RT-04).
    lookup = httpx.post(
        f"http://{AUTH_HOST}/identitytoolkit.googleapis.com/v1/projects/{PROJECT}/accounts:lookup",
        json={"localId": [alice.uid]},
        headers={"Authorization": "Bearer owner"},
    ).json()
    assert lookup["users"][0]["localId"] == alice.uid


def test_exclusao_e_idempotente_e_novo_acesso_comeca_do_zero(
    client: TestClient, auth_emulator: AuthEmulator
) -> None:
    alice = auth_emulator.create_user(name="Alice")
    first = client.get("/api/v1/me", headers=alice.headers).json()

    assert client.delete("/api/v1/me", headers=alice.headers).status_code == 204
    assert client.delete("/api/v1/me", headers=alice.headers).status_code == 204

    again = client.get("/api/v1/me", headers=alice.headers).json()
    assert again["created_at"] >= first["created_at"]


def test_exclusao_de_10_mil_documentos_em_menos_de_30_s(
    client: TestClient, auth_emulator: AuthEmulator, db: firestore.Client
) -> None:
    alice = auth_emulator.create_user()
    client.get("/api/v1/me", headers=alice.headers)
    items = db.collection("users").document(alice.uid).collection("items")
    writer = db.bulk_writer()
    for i in range(10_000):
        writer.set(items.document(f"d{i:05d}"), {"n": i})
    writer.close()  # type: ignore[no-untyped-call]

    start = time.monotonic()
    response = client.delete("/api/v1/me", headers=alice.headers)
    elapsed = time.monotonic() - start

    assert response.status_code == 204
    assert elapsed < 30, f"exclusão levou {elapsed:.1f} s"
    assert not list(items.limit(1).stream())
