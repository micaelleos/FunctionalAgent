"""Aceitação da F05 contra uma API real, com o Gemini do Vertex AI e o Jira sandbox do PO.

Pulados sem `ACCEPTANCE_API_URL`. Dois modos:
- local (`make dev` com `LLM_PROVIDER=google_vertexai` e ADC): usuários criados no emulador de Auth
  e conexão com o Jira sandbox criada pela própria API (`JIRA_SANDBOX_*` do .env.local);
- produção: `ACCEPTANCE_ID_TOKEN` de uma conta real que já tem a conexão com o sandbox (só os
  cenários de um usuário; o de isolamento usa o emulador).
"""

import json
import os
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
import pytest

API = os.environ.get("ACCEPTANCE_API_URL", "").rstrip("/")
ID_TOKEN = os.environ.get("ACCEPTANCE_ID_TOKEN")
AUTH_HOST = os.environ.get("FIREBASE_AUTH_EMULATOR_HOST")
PROJECT = os.environ.get("ACCEPTANCE_FIREBASE_PROJECT", "demo-functional-agent")
JIRA = {
    "site_url": os.environ.get("JIRA_SANDBOX_URL", ""),
    "email": os.environ.get("JIRA_SANDBOX_EMAIL", ""),
    "api_token": os.environ.get("JIRA_SANDBOX_API_TOKEN", ""),
}
JIRA_PROJECT = os.environ.get("JIRA_SANDBOX_PROJECT_KEY", "SCRUM")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if API:
        return
    skip = pytest.mark.skip(reason="aceitação: defina ACCEPTANCE_API_URL (ver tests/acceptance)")
    for item in items:
        if "tests/acceptance/" in item.nodeid:
            item.add_marker(skip)


@dataclass
class Turn:
    events: list[dict[str, Any]]
    conversation_id: str
    first_token_s: float | None

    def kinds(self) -> list[str]:
        return [e["event"] for e in self.events]

    @property
    def text(self) -> str:
        return "".join(e["data"]["text"] for e in self.events if e["event"] == "token")

    def actions(self) -> list[dict[str, Any]]:
        return [e["data"] for e in self.events if e["event"] == "action_proposed"]


class User:
    def __init__(self, token: str) -> None:
        self.headers = {"Authorization": f"Bearer {token}"}
        self.http = httpx.Client(base_url=API, timeout=httpx.Timeout(300, connect=10))

    def send(self, text: str, conversation: str = "new") -> Turn:
        import time

        events: list[dict[str, Any]] = []
        current: dict[str, Any] = {}
        started, first = time.monotonic(), None
        with self.http.stream(
            "POST",
            f"/api/v1/conversations/{conversation}/messages",
            json={"content": text},
            headers=self.headers,
        ) as response:
            assert response.status_code == 200, response.read().decode()
            cid = response.headers["x-conversation-id"]
            for line in response.iter_lines():
                if line.startswith("event: "):
                    current["event"] = line[7:]
                elif line.startswith("data: "):
                    current["data"] = json.loads(line[6:])
                elif not line and "event" in current:
                    if current["event"] == "token" and first is None:
                        first = time.monotonic() - started
                    events.append(current)
                    current = {}
        return Turn(events, cid, first)


def _emulator_user() -> str:
    assert AUTH_HOST, "modo local precisa de FIREBASE_AUTH_EMULATOR_HOST"
    base = f"http://{AUTH_HOST}/identitytoolkit.googleapis.com/v1"
    email, password = f"at-f05-{uuid.uuid4().hex[:8]}@teste.dev", uuid.uuid4().hex
    created = httpx.post(
        f"{base}/accounts:signUp?key=fake",
        json={"email": email, "password": password, "returnSecureToken": True},
    ).json()
    httpx.post(
        f"{base}/projects/{PROJECT}/accounts:update",
        json={"localId": created["localId"], "emailVerified": True},
        headers={"Authorization": "Bearer owner"},
    ).raise_for_status()
    signed = httpx.post(
        f"{base}/accounts:signInWithPassword?key=fake",
        json={"email": email, "password": password, "returnSecureToken": True},
    ).json()
    return str(signed["idToken"])


def new_user(*, with_jira: bool) -> User:
    if ID_TOKEN and with_jira:
        return User(ID_TOKEN)
    user = User(_emulator_user())
    if with_jira:
        assert all(JIRA.values()), "defina JIRA_SANDBOX_URL, _EMAIL e _API_TOKEN"
        response = user.http.post("/api/v1/jira/connections", json=JIRA, headers=user.headers)
        assert response.status_code == 201, response.text
    return user


@pytest.fixture(scope="session")
def po() -> User:
    return new_user(with_jira=True)


@pytest.fixture
def no_jira() -> User:
    return new_user(with_jira=False)
