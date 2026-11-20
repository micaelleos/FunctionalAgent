"""Dublês de teste para o verificador de token e o armazenamento de perfis."""

import copy
from typing import Any

from app.core.auth import Identity, InvalidTokenError

ALICE = Identity("uid-alice", "alice@teste.dev", True, "Alice", "password")
BOB = Identity("uid-bob", "bob@teste.dev", True, "Bob", "google.com")
UNVERIFIED = Identity("uid-carol", "carol@teste.dev", False, None, "password")


class FakeVerifier:
    """Aceita tokens no formato `ok:<nome>`; qualquer outro é inválido."""

    def __init__(self) -> None:
        self.tokens = {"ok:alice": ALICE, "ok:bob": BOB, "ok:unverified": UNVERIFIED}
        self.revoked: set[str] = set()
        self.calls: list[tuple[str, bool]] = []

    def verify(self, token: str, *, check_revoked: bool = False) -> Identity:
        self.calls.append((token, check_revoked))
        if token not in self.tokens or (check_revoked and token in self.revoked):
            raise InvalidTokenError("token inválido")
        return self.tokens[token]


class MemoryStore:
    def __init__(self) -> None:
        self.users: dict[str, dict[str, Any]] = {}

    def get_or_create(self, uid: str, profile: dict[str, Any]) -> dict[str, Any]:
        self.users.setdefault(uid, copy.deepcopy(profile))
        return copy.deepcopy(self.users[uid])

    def export(self, uid: str) -> dict[str, Any] | None:
        data = self.users.get(uid)
        return None if data is None else {"path": f"users/{uid}", "data": copy.deepcopy(data)}

    def delete(self, uid: str) -> int:
        return 1 if self.users.pop(uid, None) is not None else 0


class MemoryJiraStore:
    """Conexões Jira em memória, com a mesma interface do repositório Firestore."""

    def __init__(self) -> None:
        self.docs: dict[str, dict[str, dict[str, Any]]] = {}
        self._next = 0

    def list(self, uid: str) -> list[dict[str, Any]]:
        return [{"id": k, **copy.deepcopy(v)} for k, v in self.docs.get(uid, {}).items()]

    def get(self, uid: str, connection_id: str) -> dict[str, Any] | None:
        doc = self.docs.get(uid, {}).get(connection_id)
        return None if doc is None else {"id": connection_id, **copy.deepcopy(doc)}

    def create(self, uid: str, data: dict[str, Any]) -> str:
        self._next += 1
        connection_id = f"conn-{self._next}"
        self.docs.setdefault(uid, {})[connection_id] = copy.deepcopy(data)
        return connection_id

    def update(self, uid: str, connection_id: str, data: dict[str, Any]) -> None:
        self.docs[uid][connection_id].update(copy.deepcopy(data))

    def delete(self, uid: str, connection_id: str) -> None:
        self.docs.get(uid, {}).pop(connection_id, None)


class MemoryProjectCache:
    """Cache de projetos em memória (o real fica em `users/{uid}/cache/jiraProjects`)."""

    def __init__(self) -> None:
        self.docs: dict[str, dict[str, Any]] = {}

    def get_projects(self, uid: str) -> dict[str, Any] | None:
        doc = self.docs.get(uid)
        return copy.deepcopy(doc) if doc else None

    def set_projects(self, uid: str, data: dict[str, Any]) -> None:
        self.docs[uid] = copy.deepcopy(data)


class MemoryLinkStore:
    """`users/{uid}/project_links/{projectKey}` em memória (F19)."""

    def __init__(self) -> None:
        self.docs: dict[tuple[str, str], dict[str, Any]] = {}

    def get(self, uid: str, project_key: str) -> dict[str, Any] | None:
        doc = self.docs.get((uid, project_key))
        return dict(doc) if doc else None

    def set(self, uid: str, project_key: str, data: dict[str, Any]) -> None:
        self.docs[(uid, project_key)] = dict(data)

    def delete(self, uid: str, project_key: str) -> None:
        self.docs.pop((uid, project_key), None)
