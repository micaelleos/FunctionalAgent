"""Conversas, mensagens, ações propostas e uso do agente (03-arquitetura.md §4.3; F05).

Tudo sob `users/{uid}/…`: o `uid` vem do token, então um id de outro usuário não é encontrado.
A gestão completa de conversas (listar, renomear, excluir) é da F07.
"""

from typing import Any, cast

from google.cloud import firestore


class ConversationRepository:
    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def _user(self, uid: str) -> firestore.DocumentReference:
        return self._db.collection("users").document(uid)

    def _conversations(self, uid: str) -> firestore.CollectionReference:
        return cast(firestore.CollectionReference, self._user(uid).collection("conversations"))

    def _messages(self, uid: str, conversation_id: str) -> firestore.CollectionReference:
        ref = self._conversations(uid).document(conversation_id)
        return cast(firestore.CollectionReference, ref.collection("messages"))

    def create_conversation(self, uid: str, data: dict[str, Any]) -> str:
        ref = self._conversations(uid).document()
        ref.create(data)
        return str(ref.id)

    def get_conversation(self, uid: str, conversation_id: str) -> dict[str, Any] | None:
        snapshot = self._conversations(uid).document(conversation_id).get()
        return {"id": snapshot.id, **(snapshot.to_dict() or {})} if snapshot.exists else None

    def update_conversation(self, uid: str, conversation_id: str, data: dict[str, Any]) -> None:
        self._conversations(uid).document(conversation_id).update(data)

    def add_message(self, uid: str, conversation_id: str, data: dict[str, Any]) -> str:
        """Grava a mensagem e incrementa `messageCount` da conversa na mesma escrita em lote."""
        batch = self._db.batch()
        ref = self._messages(uid, conversation_id).document()
        batch.create(ref, data)
        batch.update(
            self._conversations(uid).document(conversation_id),
            {"messageCount": firestore.Increment(1), "updatedAt": data["createdAt"]},
        )
        batch.commit()
        return str(ref.id)

    def list_messages(self, uid: str, conversation_id: str, limit: int) -> list[dict[str, Any]]:
        """As `limit` mensagens mais recentes, da mais antiga para a mais nova."""
        query = (
            self._messages(uid, conversation_id)
            .order_by("seq", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        docs = [{"id": d.id, **(d.to_dict() or {})} for d in query.stream()]
        return list(reversed(docs))

    def create_action(self, uid: str, data: dict[str, Any]) -> str:
        ref = cast(firestore.CollectionReference, self._user(uid).collection("pending_actions"))
        doc = ref.document()
        doc.create(data)
        return str(doc.id)

    def list_actions(self, uid: str, conversation_id: str) -> list[dict[str, Any]]:
        """Ações da conversa, da mais antiga para a mais nova (igualdade simples: sem índice)."""
        ref = cast(firestore.CollectionReference, self._user(uid).collection("pending_actions"))
        query = ref.where(filter=firestore.FieldFilter("conversationId", "==", conversation_id))
        docs = [{"id": d.id, **(d.to_dict() or {})} for d in query.stream()]
        return sorted(docs, key=lambda d: d["createdAt"])

    def add_usage(self, uid: str, day: str, input_tokens: int, output_tokens: int) -> None:
        ref = self._user(uid).collection("usage").document(day)
        ref.set(
            {
                "inputTokens": firestore.Increment(input_tokens),
                "outputTokens": firestore.Increment(output_tokens),
                "messages": firestore.Increment(1),
            },
            merge=True,
        )
