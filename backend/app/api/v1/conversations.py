"""Gestão de conversas (F07): lista, criação, detalhe, renomear/fixar projeto, exclusão e histórico.

O envio de mensagens (SSE) fica em `chat.py`; as ações da conversa, em `actions.py` (F06).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel, ConfigDict, StringConstraints

from app.api.deps import Conversations, CurrentUser
from app.services.conversations import ConversationOut, ConversationPage, MessagePage

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
# Chave de projeto do Jira (ex.: SCRUM); a existência é conferida pelo agente ao propor.
ProjectKey = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]{1,9}$")]
Cursor = Annotated[
    str | None, Query(max_length=200, description="`next_cursor` da página anterior")
]

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"description": "Conversa inexistente ou de outro usuário"}
}
_PAGED: dict[int | str, dict[str, Any]] = {400: {"description": "Cursor inválido"}}


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Title | None = None
    project_key: ProjectKey | None = None


class ConversationPatch(BaseModel):
    """Só os campos enviados mudam; `project_key: null` solta o projeto fixado."""

    model_config = ConfigDict(extra="forbid")
    title: Title | None = None
    project_key: ProjectKey | None = None


@router.get("", summary="Conversas por última atividade", responses=_PAGED)
async def list_conversations(
    user: CurrentUser,
    conversations: Conversations,
    cursor: Cursor = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ConversationPage:
    return await conversations.list(user.uid, cursor, limit)


@router.post("", status_code=201, summary="Cria uma conversa (opcionalmente com projeto fixado)")
async def create_conversation(
    body: ConversationCreate, user: CurrentUser, conversations: Conversations
) -> ConversationOut:
    return await conversations.create(user.uid, body.title, body.project_key)


@router.get("/{conversation_id}", summary="Detalhe da conversa", responses=_NOT_FOUND)
async def get_conversation(
    conversation_id: str, user: CurrentUser, conversations: Conversations
) -> ConversationOut:
    return await conversations.get(user.uid, conversation_id)


@router.patch(
    "/{conversation_id}", summary="Renomeia ou fixa/solta o projeto", responses=_NOT_FOUND
)
async def update_conversation(
    conversation_id: str, body: ConversationPatch, user: CurrentUser, conversations: Conversations
) -> ConversationOut:
    changes = body.model_dump(include=body.model_fields_set)
    if changes.get("title", "") is None:
        changes.pop("title")  # título não se apaga
    return await conversations.update(user.uid, conversation_id, changes)


@router.delete(
    "/{conversation_id}",
    status_code=204,
    summary="Exclui a conversa, as mensagens e as ações (as issues continuam no Jira)",
    responses={409: {"description": "Uma ação da conversa está sendo gravada no Jira"}},
)
async def delete_conversation(
    conversation_id: str, user: CurrentUser, conversations: Conversations
) -> Response:
    await conversations.delete(user.uid, conversation_id)
    return Response(status_code=204)


@router.get(
    "/{conversation_id}/messages",
    summary="Histórico paginado, das mais recentes para as anteriores, com as ações",
    responses={**_NOT_FOUND, **_PAGED},
)
async def list_messages(
    conversation_id: str,
    user: CurrentUser,
    conversations: Conversations,
    cursor: Cursor = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
) -> MessagePage:
    return await conversations.messages(user.uid, conversation_id, cursor, limit)
