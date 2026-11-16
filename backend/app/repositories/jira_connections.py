"""Conexões Jira em `users/{uid}/jira_connections/{id}` (F04, Constituição II).

O `uid` vem sempre do token verificado; um `id` de outro usuário simplesmente não é encontrado.
"""

from typing import Any, cast

from google.cloud import firestore


class JiraConnectionRepository:
    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def _collection(self, uid: str) -> firestore.CollectionReference:
        user = self._db.collection("users").document(uid)
        return cast(firestore.CollectionReference, user.collection("jira_connections"))

    def list(self, uid: str) -> list[dict[str, Any]]:
        docs = self._collection(uid).order_by("createdAt").stream()
        return [{"id": doc.id, **(doc.to_dict() or {})} for doc in docs]

    def get(self, uid: str, connection_id: str) -> dict[str, Any] | None:
        snapshot = self._collection(uid).document(connection_id).get()
        return {"id": snapshot.id, **(snapshot.to_dict() or {})} if snapshot.exists else None

    def create(self, uid: str, data: dict[str, Any]) -> str:
        ref = self._collection(uid).document()
        ref.create(data)
        return str(ref.id)

    def update(self, uid: str, connection_id: str, data: dict[str, Any]) -> None:
        self._collection(uid).document(connection_id).update(data)

    def delete(self, uid: str, connection_id: str) -> None:
        self._collection(uid).document(connection_id).delete()
