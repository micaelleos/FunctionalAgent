"""Conversas, mensagens, ações propostas e uso do agente (03-arquitetura.md §4.3; F05).

Tudo sob `users/{uid}/…`: o `uid` vem do token, então um id de outro usuário não é encontrado.
A gestão de conversas (listar, renomear, excluir, histórico paginado) é da F07.
"""

from datetime import datetime
from typing import Any, cast

from google.cloud import firestore

DELETE_BATCH = 400  # abaixo do limite de 500 escritas por lote


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

    def list_conversations(
        self, uid: str, limit: int, after: tuple[datetime, str] | None
    ) -> list[dict[str, Any]]:
        """Por última atividade (`updatedAt desc`, empate pelo id); `after` = (updatedAt, id) do
        último item da página anterior. Índice de campo único, automático (F07-RT-02)."""
        query = (
            self._conversations(uid)
            .order_by("updatedAt", direction=firestore.Query.DESCENDING)
            .order_by("__name__", direction=firestore.Query.DESCENDING)
        )
        if after is not None:
            updated_at, last_id = after
            last = self._conversations(uid).document(last_id)
            query = query.start_after({"updatedAt": updated_at, "__name__": last})
        return [{"id": d.id, **(d.to_dict() or {})} for d in query.limit(limit).stream()]

    def set_title_if_auto(self, uid: str, conversation_id: str, title: str) -> bool:
        """Grava o título gerado só se o usuário não renomeou nesse meio-tempo (F07-RF-04)."""
        ref = self._conversations(uid).document(conversation_id)

        @firestore.transactional
        def run(transaction: firestore.Transaction) -> bool:
            snapshot = ref.get(transaction=transaction)
            if not snapshot.exists or (snapshot.to_dict() or {}).get("titleSource") == "user":
                return False
            transaction.update(ref, {"title": title, "titleSource": "auto"})
            return True

        return bool(run(self._db.transaction()))

    def delete_conversation(self, uid: str, conversation_id: str) -> None:
        """Mensagens, ações da conversa e a conversa, em lotes; repetir não falha (F07-RT-03)."""
        messages = self._messages(uid, conversation_id)
        actions = cast(firestore.CollectionReference, self._user(uid).collection("pending_actions"))
        of_conversation = actions.where(
            filter=firestore.FieldFilter("conversationId", "==", conversation_id)
        )
        for query in (messages, of_conversation):
            while True:
                refs = [d.reference for d in query.limit(DELETE_BATCH).stream()]
                if not refs:
                    break
                batch = self._db.batch()
                for ref in refs:
                    batch.delete(ref)
                batch.commit()
        # O histórico de issues (F10) fica; só perde o vínculo com a conversa (F10-RT-03).
        issues = cast(firestore.CollectionReference, self._user(uid).collection("jira_issues"))
        linked = issues.where(filter=firestore.FieldFilter("conversationId", "==", conversation_id))
        while True:
            refs = [d.reference for d in linked.limit(DELETE_BATCH).stream()]
            if not refs:
                break
            batch = self._db.batch()
            for ref in refs:
                batch.update(ref, {"conversationId": None})
            batch.commit()
        self._conversations(uid).document(conversation_id).delete()

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

    def list_messages_before(
        self, uid: str, conversation_id: str, before_seq: int | None, limit: int
    ) -> list[dict[str, Any]]:
        """Até `limit` mensagens com `seq < before_seq` (todas, se `None`), da mais nova para a
        mais antiga: o histórico carrega para cima (F07-RF-03)."""
        query = self._messages(uid, conversation_id).order_by(
            "seq", direction=firestore.Query.DESCENDING
        )
        if before_seq is not None:
            query = query.where(filter=firestore.FieldFilter("seq", "<", before_seq))
        return [{"id": d.id, **(d.to_dict() or {})} for d in query.limit(limit).stream()]

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
                # `messages` é contado na reserva, antes do turno (F11-RT-05).
            },
            merge=True,
        )
