"""Páginas do Confluence escritas pelo SpecFlow (F20-RT-07): `users/{uid}/documents/{pageId}`.

Só metadados (projeto, espaço, tipo, título, link, versão, datas); o conteúdo fica no Confluence
(Constituição II). A gravação é da confirmação (`ActionRepository.complete_doc_action`).
"""

from typing import Any, cast

from google.cloud import firestore

MAX_DOCUMENTS = 200


class DocumentRepository:
    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def _collection(self, uid: str) -> firestore.CollectionReference:
        user = self._db.collection("users").document(uid)
        return cast(firestore.CollectionReference, user.collection("documents"))

    def list_documents(self, uid: str, project_key: str | None = None) -> list[dict[str, Any]]:
        query: Any = self._collection(uid)
        if project_key:
            query = query.where(filter=firestore.FieldFilter("projectKey", "==", project_key))
        docs = [
            {"pageId": d.id, **(d.to_dict() or {})} for d in query.limit(MAX_DOCUMENTS).stream()
        ]
        return sorted(docs, key=lambda d: d.get("updatedAt") or 0, reverse=True)
