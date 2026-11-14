"""/api/v1/me com tokens e Firestore reais dos emuladores (AT-F03-02, AT-F03-03, AT-F03-04)."""

import pytest
from fastapi.testclient import TestClient
from google.cloud import firestore

from tests.integration.conftest import AuthEmulator, unsigned_token


@pytest.mark.req("F03-RF-05")
def test_perfil_criado_no_primeiro_acesso(
    client: TestClient, auth_emulator: AuthEmulator, db: firestore.Client
) -> None:
    alice = auth_emulator.create_user(name="Alice")

    response = client.get("/api/v1/me", headers=alice.headers)

    assert response.status_code == 200
    assert response.json()["email"] == alice.email
    assert response.json()["display_name"] == "Alice"
    stored = db.collection("users").document(alice.uid).get()
    data = stored.to_dict()
    assert data is not None
    assert data["locale"] == "pt-BR"


@pytest.mark.req("F03-RF-02")
def test_email_nao_verificado_recebe_403(client: TestClient, auth_emulator: AuthEmulator) -> None:
    carol = auth_emulator.create_user(verified=False)

    response = client.get("/api/v1/me", headers=carol.headers)

    assert response.status_code == 403
    assert response.json()["code"] == "email-not-verified"


@pytest.mark.parametrize(
    "token",
    [
        unsigned_token(aud="outro-projeto", iss="https://securetoken.google.com/outro-projeto"),
        "nao-e-um-jwt",
    ],
    # Expiração e assinatura: o emulador não confere; ver tests/unit/test_auth_verifier.py.
    ids=["outro-projeto", "malformado"],
)
def test_token_invalido_recebe_401(client: TestClient, token: str) -> None:
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"


def test_uid_de_outro_usuario_na_query_e_ignorado(
    client: TestClient, auth_emulator: AuthEmulator
) -> None:
    alice = auth_emulator.create_user(name="Alice")
    bob = auth_emulator.create_user(name="Bob")
    client.get("/api/v1/me", headers=bob.headers)

    response = client.get(f"/api/v1/me?uid={bob.uid}", headers=alice.headers)

    assert response.json()["uid"] == alice.uid


@pytest.mark.req("F03-RF-07")
def test_export_inclui_perfil_e_subcolecoes(
    client: TestClient, auth_emulator: AuthEmulator, db: firestore.Client
) -> None:
    alice = auth_emulator.create_user(name="Alice")
    client.get("/api/v1/me", headers=alice.headers)
    db.collection("users").document(alice.uid).collection("conversations").document("c1").set(
        {"title": "Épico de pagamentos"}
    )

    response = client.get("/api/v1/me/export", headers=alice.headers)

    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    user = response.json()["user"]
    assert user["data"]["email"] == alice.email
    assert user["collections"]["conversations"][0]["data"]["title"] == "Épico de pagamentos"
