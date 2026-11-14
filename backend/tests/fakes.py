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
