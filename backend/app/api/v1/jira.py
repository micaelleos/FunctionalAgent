"""Conexão do usuário com o Jira: `/api/v1/jira/connections` (F04)."""

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, JiraConnections
from app.services.jira_connections import JiraConnection, JiraConnectionInput

router = APIRouter(prefix="/api/v1/jira/connections", tags=["jira"])


@router.get("", response_model=list[JiraConnection], summary="Minhas conexões (sem o token)")
async def list_connections(user: CurrentUser, service: JiraConnections) -> list[JiraConnection]:
    return await service.list(user.uid)


@router.post(
    "",
    response_model=JiraConnection,
    status_code=status.HTTP_201_CREATED,
    summary="Valida a credencial no Jira e guarda a conexão (token cifrado)",
)
async def create_connection(
    body: JiraConnectionInput, user: CurrentUser, service: JiraConnections
) -> JiraConnection:
    return await service.create(user.uid, body)


@router.put("/{connection_id}", response_model=JiraConnection, summary="Troca a credencial")
async def replace_connection(
    connection_id: str, body: JiraConnectionInput, user: CurrentUser, service: JiraConnections
) -> JiraConnection:
    return await service.replace(user.uid, connection_id, body)


@router.post(
    "/{connection_id}/validate",
    response_model=JiraConnection,
    summary="Testa a credencial guardada; se o Jira recusar, a conexão fica inválida",
)
async def validate_connection(
    connection_id: str, user: CurrentUser, service: JiraConnections
) -> JiraConnection:
    return await service.validate(user.uid, connection_id)


@router.delete(
    "/{connection_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove a conexão"
)
async def delete_connection(
    connection_id: str, user: CurrentUser, service: JiraConnections
) -> Response:
    await service.delete(user.uid, connection_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
