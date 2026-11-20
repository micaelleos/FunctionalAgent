"""Vínculo projeto Jira ↔ espaço do Confluence (F19-RT-07): `users/{uid}/project_links/{key}`.

Só o vínculo: nenhum conteúdo de página é guardado (Constituição II).
"""

from typing import Any, cast

from google.cloud import firestore


class ProjectLinkRepository:
    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def _collection(self, uid: str) -> firestore.CollectionReference:
        user = self._db.collection("users").document(uid)
        return cast(firestore.CollectionReference, user.collection("project_links"))

    def get(self, uid: str, project_key: str) -> dict[str, Any] | None:
        snapshot = self._collection(uid).document(project_key).get()
        return snapshot.to_dict() if snapshot.exists else None

    def set(self, uid: str, project_key: str, data: dict[str, Any]) -> None:
        self._collection(uid).document(project_key).set(data)

    def delete(self, uid: str, project_key: str) -> None:
        self._collection(uid).document(project_key).delete()
