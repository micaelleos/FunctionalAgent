"""Vínculo projeto Jira ↔ espaço do Confluence e lista de espaços (F19-RT-08)."""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from app.api.deps import ConfluenceLinks, CurrentUser
from app.services.confluence_links import (
    ConfluenceLinkOut,
    ConfluenceSpaceOut,
    LinkInput,
    ProjectConfluenceOut,
)

router = APIRouter(tags=["confluence"])
ProjectKeyPath = Annotated[str, Path(pattern=r"^[A-Z][A-Z0-9_]{1,9}$")]


@router.get(
    "/api/v1/jira/projects/{key}/confluence",
    response_model=ProjectConfluenceOut,
    summary="Espaço do Confluence vinculado ao projeto ou, sem vínculo, a sugestão descoberta",
)
async def get_link(
    key: ProjectKeyPath, user: CurrentUser, service: ConfluenceLinks
) -> ProjectConfluenceOut:
    return await service.get(user.uid, key)


@router.put(
    "/api/v1/jira/projects/{key}/confluence",
    response_model=ConfluenceLinkOut,
    summary="Vincula o projeto a um espaço do Confluence (confere o acesso antes)",
)
async def put_link(
    key: ProjectKeyPath, body: LinkInput, user: CurrentUser, service: ConfluenceLinks
) -> ConfluenceLinkOut:
    return await service.link(user.uid, key, body)


@router.delete(
    "/api/v1/jira/projects/{key}/confluence",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desvincula o espaço do Confluence (nada muda no Confluence)",
)
async def delete_link(key: ProjectKeyPath, user: CurrentUser, service: ConfluenceLinks) -> Response:
    await service.unlink(user.uid, key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/api/v1/confluence/spaces",
    response_model=list[ConfluenceSpaceOut],
    summary="Espaços do Confluence do site (até 25), filtrados por nome ou chave",
)
async def list_spaces(
    user: CurrentUser,
    service: ConfluenceLinks,
    q: Annotated[str, Query(max_length=100)] = "",
) -> list[ConfluenceSpaceOut]:
    return await service.spaces(user.uid, q)
