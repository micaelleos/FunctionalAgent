"""Confirmação humana das ações propostas (F06, ADR-003): a única porta de escrita no Jira."""

from typing import Any

from fastapi import APIRouter

from app.api.deps import Actions, CurrentUser
from app.services.actions import ActionOut

router = APIRouter(prefix="/api/v1", tags=["actions"])

_PROBLEMS: dict[int | str, dict[str, Any]] = {
    404: {"description": "Ação inexistente ou de outro usuário"},
    409: {"description": "Já concluída, recusada ou em execução; `action` traz o estado"},
    410: {"description": "Expirada (24 h)"},
}


@router.post(
    "/actions/{action_id}/confirm",
    summary="Confirma e executa a ação exatamente como exibida",
    responses={
        **_PROBLEMS,
        422: {"description": "O Jira não executou; `detail` traz o erro traduzido"},
        503: {"description": "Escritas no Jira desligadas"},
    },
)
async def confirm(action_id: str, user: CurrentUser, actions: Actions) -> ActionOut:
    return await actions.confirm(user.uid, action_id)


@router.post(
    "/actions/{action_id}/reject",
    summary="Recusa a ação; nada é escrito no Jira",
    responses=_PROBLEMS,
)
async def reject(action_id: str, user: CurrentUser, actions: Actions) -> ActionOut:
    return await actions.reject(user.uid, action_id)


@router.get(
    "/conversations/{conversation_id}/actions",
    summary="Ações propostas na conversa, para reidratar os cartões",
)
async def list_actions(
    conversation_id: str, user: CurrentUser, actions: Actions
) -> list[ActionOut]:
    return await actions.list(user.uid, conversation_id)
