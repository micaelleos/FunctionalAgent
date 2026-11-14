"""Conta do usuário: perfil, exportação e exclusão dos dados do SpecFlow AI (F03).

A exclusão apaga só os dados deste app. O login é do Auth compartilhado do portfólio e continua
valendo nos outros apps; por isso não há `auth.delete_user` nem revogação de sessões (F03-RT-04).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel

from app.core.auth import Identity


class Profile(BaseModel):
    uid: str
    display_name: str | None
    email: str | None
    created_at: datetime
    locale: str


class UserStore(Protocol):
    def get_or_create(self, uid: str, profile: dict[str, Any]) -> dict[str, Any]: ...
    def export(self, uid: str) -> dict[str, Any] | None: ...
    def delete(self, uid: str) -> int: ...


class AccountService:
    def __init__(self, store: UserStore, clock: Callable[[], datetime] | None = None) -> None:
        self._store = store
        self._clock = clock or (lambda: datetime.now(UTC))

    def profile(self, identity: Identity) -> Profile:
        """Devolve o perfil, criando-o no primeiro acesso (F03-RF-05)."""
        new = {
            "displayName": identity.name or (identity.email or "").split("@")[0] or None,
            "email": identity.email,
            "createdAt": self._clock(),
            "locale": "pt-BR",
        }
        stored = self._store.get_or_create(identity.uid, new)
        return Profile(
            uid=identity.uid,
            display_name=stored.get("displayName"),
            email=stored.get("email"),
            created_at=stored["createdAt"],
            locale=stored.get("locale", "pt-BR"),
        )

    def export(self, identity: Identity) -> dict[str, Any]:
        """Todos os dados do usuário neste app, em JSON (F03-RF-07)."""
        return {
            "app": "SpecFlow AI",
            "exportedAt": self._clock().isoformat(),
            "uid": identity.uid,
            "user": self._store.export(identity.uid),
        }

    def delete(self, identity: Identity) -> int:
        """Apaga todos os dados do usuário neste app; idempotente (F03-RF-08)."""
        return self._store.delete(identity.uid)
