"""Perfis em `users/{uid}` no banco Firestore do app (F03-RF-05, F03-RF-07, F03-RF-08).

Todo dado do usuário fica abaixo de `users/{uid}` (Constituição II): exportar e excluir é
percorrer essa árvore.
"""

import contextlib
from datetime import datetime
from typing import Any

from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore


def _plain(value: Any) -> Any:
    """Converte valores do Firestore em JSON (datas em ISO 8601, referências em caminho)."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, firestore.DocumentReference):
        return value.path
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


class UserRepository:
    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def _ref(self, uid: str) -> firestore.DocumentReference:
        return self._db.collection("users").document(uid)

    def get(self, uid: str) -> dict[str, Any] | None:
        snapshot = self._ref(uid).get()
        return snapshot.to_dict() if snapshot.exists else None

    def get_or_create(self, uid: str, profile: dict[str, Any]) -> dict[str, Any]:
        """Cria o perfil se ainda não existe; com chamadas simultâneas, só a primeira grava."""
        with contextlib.suppress(AlreadyExists):
            self._ref(uid).create(profile)
        stored = self.get(uid)
        return stored if stored is not None else profile

    def export(self, uid: str) -> dict[str, Any] | None:
        ref = self._ref(uid)
        snapshot = ref.get()
        if not snapshot.exists:
            return None
        return {"path": ref.path, "data": _plain(snapshot.to_dict()), **self._children(ref)}

    def _children(self, ref: firestore.DocumentReference) -> dict[str, Any]:
        collections: dict[str, Any] = {}
        for collection in ref.collections():
            docs = []
            for doc in collection.stream():
                docs.append(
                    {"id": doc.id, "data": _plain(doc.to_dict()), **self._children(doc.reference)}
                )
            collections[collection.id] = docs
        return {"collections": collections} if collections else {}

    def delete(self, uid: str) -> int:
        """Apaga `users/{uid}` e todas as subcoleções; devolve quantos documentos apagou."""
        return int(self._db.recursive_delete(self._ref(uid)))
