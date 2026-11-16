"""Eventos SSE do chat (03-arquitetura.md §3.5, F05-RT-12), versão 1.

O esquema é publicado em `docs/api/sse-events.v1.json` e conferido pelo teste de contrato: mudar
um evento de forma incompatível exige `v2` (Constituição V).
"""

import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

SCHEMA_VERSION = 1


class _Event(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TokenEvent(_Event):
    event: Literal["token"] = "token"
    text: str


class ToolStartEvent(_Event):
    event: Literal["tool_start"] = "tool_start"
    name: str
    summary: str


class ToolEndEvent(_Event):
    event: Literal["tool_end"] = "tool_end"
    name: str
    summary: str


class ActionProposedEvent(_Event):
    event: Literal["action_proposed"] = "action_proposed"
    action_id: str
    kind: Literal["create_issue", "update_issue"]
    preview: dict[str, Any] = Field(
        description="project_key/issue_key, issue_type, summary, markdown, readiness, labels"
    )


class MessageSavedEvent(_Event):
    event: Literal["message_saved"] = "message_saved"
    message_id: str
    conversation_id: str
    user_message_id: str


class ErrorEvent(_Event):
    event: Literal["error"] = "error"
    code: Literal[
        "llm-unavailable", "turn-timeout", "tool-limit", "jira-auth", "internal", "quota-exceeded"
    ]
    message: str


class Usage(_Event):
    input_tokens: int
    output_tokens: int
    cost_usd: float


class DoneEvent(_Event):
    event: Literal["done"] = "done"
    usage: Usage


ChatEvent = Annotated[
    TokenEvent
    | ToolStartEvent
    | ToolEndEvent
    | ActionProposedEvent
    | MessageSavedEvent
    | ErrorEvent
    | DoneEvent,
    Field(discriminator="event"),
]
CHAT_EVENT: TypeAdapter[ChatEvent] = TypeAdapter(ChatEvent)


def to_sse(event: BaseModel) -> dict[str, str]:
    """Formato do `sse-starlette`: `event:` é o tipo; `data:` é o JSON sem o campo `event`."""
    data = event.model_dump(mode="json", exclude={"event"})
    return {"event": str(getattr(event, "event")), "data": json.dumps(data, ensure_ascii=False)}  # noqa: B009


def json_schema() -> dict[str, Any]:
    schema = CHAT_EVENT.json_schema()
    schema["$id"] = f"https://specsflow-ai.web.app/schemas/sse-events.v{SCHEMA_VERSION}.json"
    schema["title"] = f"Eventos SSE do chat v{SCHEMA_VERSION}"
    return schema
