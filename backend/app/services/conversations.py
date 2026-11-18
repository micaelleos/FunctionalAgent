"""Gestão de conversas (F07): listar, criar, abrir, renomear, fixar projeto, excluir e histórico.

O envio de mensagens (e a criação implícita com `id=new`) continua em `services/chat.py` (F05).
"""

import base64
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel

from app.core.errors import ApiProblemError
from app.core.telemetry import in_thread
from app.services.actions import ActionOut, to_out
from app.services.chat import ConversationNotFoundError

DEFAULT_TITLE = "Nova conversa"
VISIBLE_ROLES = ("user", "assistant")
# Notas que o histórico guarda para o modelo ("[Ação proposta …]"); não são do usuário.
_ACTION_NOTE = re.compile(r"^\[Ação proposta [^\n]*\]$", re.MULTILINE)
_SCAN = 100  # mensagens lidas por vez ao montar uma página do histórico


class ConversationStore(Protocol):
    def create_conversation(self, uid: str, data: dict[str, Any]) -> str: ...
    def get_conversation(self, uid: str, conversation_id: str) -> dict[str, Any] | None: ...
    def update_conversation(self, uid: str, conversation_id: str, data: dict[str, Any]) -> None: ...
    def list_conversations(
        self, uid: str, limit: int, after: tuple[datetime, str] | None
    ) -> list[dict[str, Any]]: ...
    def list_messages_before(
        self, uid: str, conversation_id: str, before_seq: int | None, limit: int
    ) -> list[dict[str, Any]]: ...
    def list_actions(self, uid: str, conversation_id: str) -> list[dict[str, Any]]: ...
    def delete_conversation(self, uid: str, conversation_id: str) -> None: ...


class ConversationOut(BaseModel):
    id: str
    title: str
    project_key: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int


class ConversationPage(BaseModel):
    items: list[ConversationOut]
    next_cursor: str | None


class MessageOut(BaseModel):
    """Mensagem como o usuário a viu; `actions` traz o cartão de cada proposta (F07-RF-03)."""

    id: str
    role: Literal["user", "assistant"]
    text: str
    created_at: datetime
    actions: list[ActionOut]
    # O usuário parou a resposta (ou fechou a aba) no meio: o texto é parcial (F08-RT-09).
    interrupted: bool = False


class MessagePage(BaseModel):
    """Da mais antiga para a mais nova; `next_cursor` leva às anteriores."""

    items: list[MessageOut]
    next_cursor: str | None


class InvalidCursorError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(400, "invalid-cursor", "Cursor de paginação inválido")


class ConversationBusyError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(
            409,
            "conversation-busy",
            "Conversa com ação em execução",
            "Uma ação desta conversa está sendo gravada no Jira. Tente excluir em instantes.",
        )


def _encode(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode(cursor: str) -> dict[str, Any]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidCursorError() from exc
    if not isinstance(data, dict):
        raise InvalidCursorError()
    return data


def _conversation_cursor(cursor: str | None) -> tuple[datetime, str] | None:
    if cursor is None:
        return None
    data = _decode(cursor)
    try:
        return datetime.fromisoformat(str(data["u"])), str(data["i"])
    except (KeyError, ValueError) as exc:
        raise InvalidCursorError() from exc


def _message_cursor(cursor: str | None) -> int | None:
    if cursor is None:
        return None
    seq = _decode(cursor).get("s")
    if not isinstance(seq, int) or seq < 1:
        raise InvalidCursorError()
    return seq


def display_text(doc: dict[str, Any]) -> str:
    """O texto que o usuário viu: `text` (desde a F07) ou `content` sem as notas para o modelo."""
    if isinstance(doc.get("text"), str):
        return str(doc["text"])
    return _ACTION_NOTE.sub("", str(doc.get("content", ""))).strip()


def conversation_out(doc: dict[str, Any]) -> ConversationOut:
    return ConversationOut(
        id=doc["id"],
        title=str(doc.get("title") or DEFAULT_TITLE),
        project_key=doc.get("projectKey"),
        created_at=doc["createdAt"],
        updated_at=doc.get("updatedAt") or doc["createdAt"],
        message_count=int(doc.get("messageCount", 0)),
    )


class ConversationService:
    def __init__(
        self, store: ConversationStore, clock: Callable[[], datetime] | None = None
    ) -> None:
        self._store = store
        self._clock = clock or (lambda: datetime.now(UTC))

    async def _run[T](self, fn: Callable[..., T], *args: Any) -> T:
        return await in_thread(fn, *args)

    async def _get(self, uid: str, conversation_id: str) -> dict[str, Any]:
        doc = await self._run(self._store.get_conversation, uid, conversation_id)
        if doc is None:
            raise ConversationNotFoundError()
        return doc

    async def list(self, uid: str, cursor: str | None, limit: int) -> ConversationPage:
        after = _conversation_cursor(cursor)
        docs = await self._run(self._store.list_conversations, uid, limit + 1, after)
        page, more = docs[:limit], len(docs) > limit
        next_cursor = None
        if more:
            last = page[-1]
            updated = last.get("updatedAt") or last["createdAt"]
            next_cursor = _encode({"u": updated.isoformat(), "i": last["id"]})
        return ConversationPage(items=[conversation_out(d) for d in page], next_cursor=next_cursor)

    async def create(self, uid: str, title: str | None, project_key: str | None) -> ConversationOut:
        now = self._clock()
        data: dict[str, Any] = {
            "title": title or DEFAULT_TITLE,
            "titleSource": "user" if title else "auto",
            "projectKey": project_key,
            "createdAt": now,
            "updatedAt": now,
            "messageCount": 0,
            "summary": "",
            "summarizedThrough": 0,
        }
        conversation_id = await self._run(self._store.create_conversation, uid, data)
        return conversation_out({"id": conversation_id, **data})

    async def get(self, uid: str, conversation_id: str) -> ConversationOut:
        return conversation_out(await self._get(uid, conversation_id))

    async def update(
        self, uid: str, conversation_id: str, changes: dict[str, Any]
    ) -> ConversationOut:
        """`changes` só com os campos enviados: `title` renomeia; `project_key` fixa ou solta
        (`None`). Renomear não conta como atividade (não sobe na lista)."""
        doc = await self._get(uid, conversation_id)
        data: dict[str, Any] = {}
        if "title" in changes:
            data |= {"title": changes["title"], "titleSource": "user"}
        if "project_key" in changes:
            data["projectKey"] = changes["project_key"]
        if data:
            await self._run(self._store.update_conversation, uid, conversation_id, data)
        return conversation_out(doc | data)

    async def delete(self, uid: str, conversation_id: str) -> None:
        """Idempotente: excluir de novo (ou o que não existe) não falha (F07-RT-03)."""
        actions = await self._run(self._store.list_actions, uid, conversation_id)
        if any(a.get("status") == "executing" for a in actions):
            raise ConversationBusyError()
        await self._run(self._store.delete_conversation, uid, conversation_id)

    async def messages(
        self, uid: str, conversation_id: str, cursor: str | None, limit: int
    ) -> MessagePage:
        before = _message_cursor(cursor)
        await self._get(uid, conversation_id)
        visible: list[dict[str, Any]] = []
        more = False
        while True:
            batch = await self._run(
                self._store.list_messages_before, uid, conversation_id, before, _SCAN
            )
            for doc in batch:
                if doc.get("role") not in VISIBLE_ROLES:
                    continue
                if len(visible) == limit:
                    more = True
                    break
                visible.append(doc)
            if more or len(batch) < _SCAN:
                break
            before = int(batch[-1]["seq"])
        now = self._clock()
        actions = {
            a["id"]: to_out(a, now)
            for a in await self._run(self._store.list_actions, uid, conversation_id)
        }
        items = [
            MessageOut(
                id=d["id"],
                role=d["role"],
                text=display_text(d),
                created_at=d["createdAt"],
                interrupted=bool(d.get("interrupted")),
                actions=[actions[a["id"]] for a in d.get("actions") or [] if a["id"] in actions],
            )
            for d in reversed(visible)
        ]
        next_cursor = _encode({"s": int(visible[-1]["seq"])}) if more else None
        return MessagePage(items=items, next_cursor=next_cursor)
