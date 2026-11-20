"""Ações propostas, issues criadas e mensagens de sistema da confirmação (F06, ADR-003).

`users/{uid}/pending_actions/{id}`: as transições de estado rodam numa transação do Firestore, o
que garante uma única execução mesmo com várias confirmações em paralelo (F06-RT-01).
`users/{uid}/jira_issues/{key}`: issues criadas ou atualizadas pelo SpecFlow (F10).
`users/{uid}/documents/{pageId}`: páginas do Confluence escritas pelo SpecFlow (F20-RT-07).
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

    def _issues(self, uid: str) -> firestore.CollectionReference:
        return cast(firestore.CollectionReference, self._user(uid).collection("jira_issues"))

    def complete_action(
        self,
        uid: str,
        action_id: str,
        change: dict[str, Any],
        issue_key: str,
        issue: dict[str, Any],
        first_time: dict[str, Any],
    ) -> None:
        """Conclui a ação e grava o registro da issue na mesma transação (F10-RT-01).

        `first_time` só entra se a issue ainda não está no histórico (a data da 1ª gravação não
        muda numa atualização)."""
        action = self._actions(uid).document(action_id)
        record = self._issues(uid).document(issue_key)

        @firestore.transactional
        def run(transaction: firestore.Transaction) -> None:
            exists = record.get(transaction=transaction).exists
            transaction.update(action, change)
            transaction.set(record, issue if exists else {**first_time, **issue}, merge=True)

        run(self._db.transaction(max_attempts=MAX_ATTEMPTS))

    def _documents(self, uid: str) -> firestore.CollectionReference:
        return cast(firestore.CollectionReference, self._user(uid).collection("documents"))

    def complete_doc_action(
        self, uid: str, action_id: str, change: dict[str, Any], documents: dict[str, dict[str, Any]]
    ) -> None:
        """Conclui uma ação do Confluence e grava o registro das páginas na mesma transação
        (F20-RT-07). `createdAt` só entra na 1ª vez que o SpecFlow escreve a página."""
        action = self._actions(uid).document(action_id)
        refs = {page_id: self._documents(uid).document(page_id) for page_id in documents}

        @firestore.transactional
        def run(transaction: firestore.Transaction) -> None:
            existing = {pid: ref.get(transaction=transaction).exists for pid, ref in refs.items()}
            transaction.update(action, change)
            for page_id, ref in refs.items():
                record = dict(documents[page_id])
                if existing[page_id]:
                    record.pop("createdAt", None)
                transaction.set(ref, record, merge=True)

        run(self._db.transaction(max_attempts=MAX_ATTEMPTS))

    def get_issue(self, uid: str, key: str) -> dict[str, Any] | None:
        snapshot = self._issues(uid).document(key).get()
        return {"key": snapshot.id, **(snapshot.to_dict() or {})} if snapshot.exists else None

    def list_issues(
        self,
        uid: str,
        limit: int,
        after: tuple[Any, str] | None,
        since: Any | None,
        until: Any | None,
    ) -> list[dict[str, Any]]:
        """Do mais recente ao mais antigo (`createdAt`, depois a chave); período na consulta."""
        query: Any = self._issues(uid)
        if since is not None:
            query = query.where(filter=firestore.FieldFilter("createdAt", ">=", since))
        if until is not None:
            query = query.where(filter=firestore.FieldFilter("createdAt", "<", until))
        query = query.order_by("createdAt", direction=firestore.Query.DESCENDING).order_by(
            "__name__", direction=firestore.Query.DESCENDING
        )
        if after is not None:
            created, key = after
            query = query.start_after(
                {"createdAt": created, "__name__": self._issues(uid).document(key)}
            )
        return [{"key": d.id, **(d.to_dict() or {})} for d in query.limit(limit).stream()]

    def conversation_titles(self, uid: str, ids: list[str]) -> dict[str, str]:
        refs = [self._conversations(uid).document(i) for i in ids]
        return {
            s.id: str((s.to_dict() or {}).get("title") or "")
            for s in self._db.get_all(refs)
            if s.exists
        }

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
