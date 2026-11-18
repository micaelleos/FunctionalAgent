"""Uso diário por usuário: `users/{uid}/usage/{dia}` (F05-RT-07, F11-RT-05/06).

Cota e rate limit ficam no mesmo documento e são decididos numa transação: várias instâncias do
Cloud Run veem o mesmo contador, sem estado em memória (Art. II.3) e sem Redis (Art. VII).
"""

import random
import time
from collections.abc import Callable
from typing import Any, cast

from google.cloud import firestore

Decide = Callable[[dict[str, Any]], tuple[dict[str, Any] | None, Any]]
ROUNDS = 3


class UsageConflictError(Exception):
    """Muitas mensagens do mesmo usuário ao mesmo tempo: a transação não conseguiu gravar."""


class UsageRepository:
    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def _usage(self, uid: str) -> firestore.CollectionReference:
        users = self._db.collection("users")
        return cast(firestore.CollectionReference, users.document(uid).collection("usage"))

    def update_usage(self, uid: str, day: str, decide: Decide) -> Any:
        """Lê o dia, pergunta a `decide` o que gravar (merge) e devolve o resultado dela."""
        ref = self._usage(uid).document(day)

        @firestore.transactional
        def run(transaction: firestore.Transaction) -> Any:
            snapshot = ref.get(transaction=transaction)
            change, result = decide(snapshot.to_dict() or {} if snapshot.exists else {})
            if change:
                transaction.set(ref, change, merge=True)
            return result

        for round_ in range(ROUNDS):
            try:
                return run(self._db.transaction(max_attempts=5))
            except ValueError as exc:  # "Failed to commit transaction": colisões em sequência
                if "Failed to commit transaction" not in str(exc):
                    raise
                time.sleep(random.uniform(0.05, 0.2) * (round_ + 1))  # noqa: S311 - só espera
        raise UsageConflictError(uid)

    def usage_days(self, uid: str, days: list[str]) -> dict[str, dict[str, Any]]:
        refs = [self._usage(uid).document(d) for d in days]
        return {s.id: s.to_dict() or {} for s in self._db.get_all(refs) if s.exists}
