"""Chat com o agente em streaming: `POST /api/v1/conversations/{id}/messages` (F05, ADR-002)."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, StringConstraints
from sse_starlette import EventSourceResponse

from app.api.deps import Chat, CurrentUser
from app.services.chat_events import SCHEMA_VERSION, to_sse

router = APIRouter(prefix="/api/v1/conversations", tags=["chat"])


class MessageInput(BaseModel):
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]


@router.post(
    "/{conversation_id}/messages",
    summary="Envia uma mensagem e recebe a resposta do agente em SSE",
    description=(
        "`conversation_id = new` cria a conversa. Eventos: token, tool_start, tool_end, "
        "action_proposed, message_saved, error, done (esquema em docs/api/sse-events.v1.json)."
    ),
    response_class=EventSourceResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def send_message(
    conversation_id: str, body: MessageInput, user: CurrentUser, chat: Chat
) -> EventSourceResponse:
    conversation, events = await chat.open_turn(user.uid, conversation_id, body.content)

    async def stream() -> AsyncIterator[dict[str, str]]:
        async for event in events:
            yield to_sse(event)

    return EventSourceResponse(
        stream(),
        ping=15,
        headers={
            "X-Conversation-Id": conversation,
            "X-Sse-Schema-Version": str(SCHEMA_VERSION),
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
