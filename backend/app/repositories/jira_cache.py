"""Cache da lista de projetos em `users/{uid}/cache/jiraProjects` (F09-RT-01, Constituição II).

No Firestore, e não na memória do processo (Art. II.3): vale para todas as instâncias e some com
a conta (a exclusão da F03 é recursiva).
"""

from typing import Any, cast

from google.cloud import firestore

DOC = "jiraProjects"


class JiraCacheRepository:
    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def _ref(self, uid: str) -> firestore.DocumentReference:
        cache = self._db.collection("users").document(uid).collection("cache")
        return cast(firestore.DocumentReference, cache.document(DOC))

    def get_projects(self, uid: str) -> dict[str, Any] | None:
        snapshot = self._ref(uid).get()
        return snapshot.to_dict() if snapshot.exists else None

    def set_projects(self, uid: str, data: dict[str, Any]) -> None:
        self._ref(uid).set(data)
