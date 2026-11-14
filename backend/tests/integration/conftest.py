"""Testes contra os emuladores de Auth e Firestore (`docker compose up emulators` ou CI).

Sem `FIREBASE_AUTH_EMULATOR_HOST` e `FIRESTORE_EMULATOR_HOST`, os testes daqui são pulados.
"""

import base64
import json
import os
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from google.cloud import firestore

from app.core.config import Settings, get_settings
from app.main import create_app

PROJECT = "demo-functional-agent"
DATABASE = "specflow"
AUTH_HOST = os.environ.get("FIREBASE_AUTH_EMULATOR_HOST")
FIRESTORE_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if AUTH_HOST and FIRESTORE_HOST:
        return
    skip = pytest.mark.skip(reason="emuladores do Firebase não configurados (make test os sobe)")
    for item in items:
        if "tests/integration/" in item.nodeid:
            item.add_marker(skip)


@dataclass
class EmulatorUser:
    uid: str
    email: str
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


class AuthEmulator:
    def __init__(self, host: str) -> None:
        self._base = f"http://{host}"
        self._http = httpx.Client(timeout=10)

    def _identity(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}/identitytoolkit.googleapis.com/v1/{path}?key=fake-api-key"
        response = self._http.post(url, json=body)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    def create_user(self, *, verified: bool = True, name: str = "Teste") -> EmulatorUser:
        email = f"e2e-{uuid.uuid4().hex[:8]}@teste.dev"
        password = uuid.uuid4().hex  # só existe no emulador
        created = self._identity(
            "accounts:signUp", {"email": email, "password": password, "returnSecureToken": True}
        )
        update: dict[str, Any] = {"localId": created["localId"], "displayName": name}
        if verified:
            update["emailVerified"] = True
        response = self._http.post(
            f"{self._base}/identitytoolkit.googleapis.com/v1/projects/{PROJECT}/accounts:update",
            json=update,
            headers={"Authorization": "Bearer owner"},
        )
        response.raise_for_status()
        signed = self._identity(
            "accounts:signInWithPassword",
            {"email": email, "password": password, "returnSecureToken": True},
        )
        return EmulatorUser(created["localId"], email, signed["idToken"])

    def clear(self) -> None:
        self._http.delete(f"{self._base}/emulator/v1/projects/{PROJECT}/accounts")


def unsigned_token(**claims: Any) -> str:
    """Token sem assinatura, como os do emulador, com claims arbitrárias."""

    def enc(part: dict[str, Any]) -> str:
        raw = json.dumps(part).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    now = int(time.time())
    payload = {
        "aud": PROJECT,
        "iss": f"https://securetoken.google.com/{PROJECT}",
        "sub": "uid-forjado",
        "user_id": "uid-forjado",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
        "email": "forjado@teste.dev",
        "email_verified": True,
        "firebase": {"sign_in_provider": "password", "identities": {}},
    }
    payload.update(claims)
    return f"{enc({'alg': 'none', 'typ': 'JWT'})}.{enc(payload)}."


@pytest.fixture(scope="session")
def auth_emulator() -> AuthEmulator:
    assert AUTH_HOST
    return AuthEmulator(AUTH_HOST)


@pytest.fixture(scope="session")
def db() -> firestore.Client:
    return firestore.Client(project=PROJECT, database=DATABASE)


@pytest.fixture(autouse=True)
def _clean(auth_emulator: AuthEmulator) -> Iterator[None]:
    yield
    auth_emulator.clear()
    httpx.delete(
        f"http://{FIRESTORE_HOST}/emulator/v1/projects/{PROJECT}/databases/{DATABASE}/documents"
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    settings = Settings(env="test", gcp_project=PROJECT, firestore_database=DATABASE)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        yield c
