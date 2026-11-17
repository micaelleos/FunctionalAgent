"""Ações propostas, issues criadas e mensagens de sistema da confirmação (F06, ADR-003).

`users/{uid}/pending_actions/{id}`: as transições de estado rodam numa transação do Firestore, o
que garante uma única execução mesmo com várias confirmações em paralelo (F06-RT-01).
`users/{uid}/jira_issues/{key}`: issues criadas pelo SpecFlow (base da F10).
"""

from collections.abc import Callable
from typing import Any, cast

from google.cloud import firestore

from app.repositories.conversations import ConversationRepository

Decide = Callable[[dict[str, Any] | None], dict[str, Any] | None]
MAX_ATTEMPTS = 10


class TransitionConflictError(Exception):
    """A transação colidiu com outras até desistir (cliques simultâneos na mesma ação). Outra
    transação venceu: quem chamou relê a ação e responde com o estado atual."""


class ActionRepository(ConversationRepository):
    def _actions(self, uid: str) -> firestore.CollectionReference:
        return cast(firestore.CollectionReference, self._user(uid).collection("pending_actions"))

    def get_action(self, uid: str, action_id: str) -> dict[str, Any] | None:
        snapshot = self._actions(uid).document(action_id).get()
        return {"id": snapshot.id, **(snapshot.to_dict() or {})} if snapshot.exists else None

    def transition(self, uid: str, action_id: str, decide: Decide) -> dict[str, Any] | None:
        """Lê a ação, pergunta a `decide` o que mudar e grava, tudo na mesma transação.

        `decide` recebe a ação atual (ou `None`) e devolve os campos a mudar (ou `None`). Pode
        rodar mais de uma vez se a transação colidir, então não deve ter efeitos colaterais.
        Devolve a ação depois da mudança, ou `None` se ela não existe."""
        ref = self._actions(uid).document(action_id)

        @firestore.transactional
        def run(transaction: firestore.Transaction) -> dict[str, Any] | None:
            snapshot = ref.get(transaction=transaction)
            current = {"id": snapshot.id, **(snapshot.to_dict() or {})} if snapshot.exists else None
            change = decide(current)
            if current is None:
                return None
            if change:
                transaction.update(ref, change)
                current = {**current, **change}
            return current

        try:
            return cast(dict[str, Any] | None, run(self._db.transaction(max_attempts=MAX_ATTEMPTS)))
        except ValueError as exc:  # o cliente sinaliza "Failed to commit transaction" assim
            if "Failed to commit transaction" not in str(exc):
                raise
            raise TransitionConflictError(action_id) from exc

    def update_action(self, uid: str, action_id: str, data: dict[str, Any]) -> None:
        self._actions(uid).document(action_id).update(data)

    def save_issue(self, uid: str, key: str, data: dict[str, Any]) -> None:
        self._user(uid).collection("jira_issues").document(key).set(data, merge=True)

    def add_system_message(self, uid: str, conversation_id: str, data: dict[str, Any]) -> str:
        """Mensagem `role=system` no fim da conversa, com `seq` e `messageCount` na mesma
        transação."""
        conversation = self._conversations(uid).document(conversation_id)
        message = self._messages(uid, conversation_id).document()

        @firestore.transactional
        def run(transaction: firestore.Transaction) -> None:
            snapshot = conversation.get(transaction=transaction)
            if not snapshot.exists:  # conversa excluída enquanto o Jira gravava (F07-RT-03)
                return
            count = int((snapshot.to_dict() or {}).get("messageCount", 0))
            transaction.create(message, {**data, "role": "system", "seq": count + 1})
            transaction.update(
                conversation,
                {"messageCount": firestore.Increment(1), "updatedAt": data["createdAt"]},
            )

        run(self._db.transaction())
        return str(message.id)
