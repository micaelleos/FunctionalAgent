"""Vínculo projeto Jira ↔ espaço do Confluence (F19-RF-01, F19-RF-02, F19-RT-07, F19-RT-08).

A descoberta só sugere; o vínculo é salvo quando o usuário confirma (Constituição IV). Ordem:
vínculo salvo → espaço com a mesma chave do projeto → página com o rótulo
`specflow-projeto-<chave>`. Usa a credencial da conexão Atlassian da F04.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from app.core.errors import ApiProblemError
from app.core.telemetry import in_thread
from app.integrations.confluence.client import (
    ConfluenceAuthError,
    ConfluenceClient,
    ConfluenceError,
    ConfluenceNotFoundError,
    ConfluenceSpace,
    cql_string,
)
from app.services.confluence_reader import ConfluenceReaderAdapter
from app.services.jira_connections import JiraConnectionService, UnreachableError
from app.services.jira_projects import JiraNotConnectedError

log = logging.getLogger("app.confluence")

LinkSource = Literal["same-key", "label", "manual"]
MAX_SPACES_OUT = 25


class ConfluenceSpaceOut(BaseModel):
    key: str
    name: str
    url: str


class ConfluenceLinkOut(BaseModel):
    space: ConfluenceSpaceOut
    source: LinkSource
    linked_at: datetime


class ConfluenceSuggestionOut(BaseModel):
    space: ConfluenceSpaceOut
    source: Literal["same-key", "label"]


class ProjectConfluenceOut(BaseModel):
    link: ConfluenceLinkOut | None
    suggestion: ConfluenceSuggestionOut | None
    # `False` quando a conta não tem acesso ao Confluence do site (F19-RF-09).
    available: bool = True


class LinkInput(BaseModel):
    space_key: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9~_-]+$")


class ConfluenceForbiddenError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(
            403,
            "confluence-forbidden",
            "Sem acesso ao Confluence",
            "A sua conta Atlassian não tem acesso ao Confluence deste site (ou a este espaço).",
        )


class SpaceNotFoundError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(
            404,
            "confluence-space-not-found",
            "Espaço não encontrado",
            "Esse espaço não existe no Confluence ou a sua conta não tem acesso a ele.",
        )


class LinkStore(Protocol):
    def get(self, uid: str, project_key: str) -> dict[str, Any] | None: ...
    def set(self, uid: str, project_key: str, data: dict[str, Any]) -> None: ...
    def delete(self, uid: str, project_key: str) -> None: ...


def project_label(project_key: str) -> str:
    return f"specflow-projeto-{project_key.lower()}"


def _space_out(space: ConfluenceSpace) -> ConfluenceSpaceOut:
    return ConfluenceSpaceOut(key=space.key, name=space.name, url=space.url)


def _link_out(doc: dict[str, Any]) -> ConfluenceLinkOut:
    return ConfluenceLinkOut(
        space=ConfluenceSpaceOut(key=doc["spaceKey"], name=doc["spaceName"], url=doc["spaceUrl"]),
        source=doc.get("source", "manual"),
        linked_at=doc["linkedAt"],
    )


class ConfluenceLinkService:
    def __init__(
        self,
        store: LinkStore,
        connections: JiraConnectionService,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._connections = connections
        self._clock = clock or (lambda: datetime.now(UTC))

    async def _connection_id(self, uid: str) -> str:
        connections = await self._connections.list(uid)
        if not connections:
            raise JiraNotConnectedError()
        return connections[0].id  # MVP: uma conexão por usuário (F04)

    async def _client(self, uid: str) -> tuple[str, ConfluenceClient]:
        connection_id = await self._connection_id(uid)
        return connection_id, await self._connections.confluence_client_for(uid, connection_id)

    async def _discover(
        self, client: ConfluenceClient, project_key: str
    ) -> ConfluenceSuggestionOut | None:
        space = await client.space_by_key(project_key)
        if space is not None:
            return ConfluenceSuggestionOut(space=_space_out(space), source="same-key")
        cql = f"type = page AND label = {cql_string(project_label(project_key))}"
        pages = await client.search(cql, 1)
        if pages:
            space_id = await client.page_space_id(pages[0].id)
            if space_id:
                found = await client.space_by_id(space_id)
                return ConfluenceSuggestionOut(space=_space_out(found), source="label")
        return None

    async def get(self, uid: str, project_key: str) -> ProjectConfluenceOut:
        doc = await in_thread(self._store.get, uid, project_key)
        if doc:
            return ProjectConfluenceOut(link=_link_out(doc), suggestion=None)
        _, client = await self._client(uid)
        async with client:
            try:
                suggestion = await self._discover(client, project_key)
            except ConfluenceAuthError:
                return ProjectConfluenceOut(link=None, suggestion=None, available=False)
            except ConfluenceNotFoundError:
                # Sem o produto Confluence no site, `/wiki` responde 404.
                return ProjectConfluenceOut(link=None, suggestion=None, available=False)
            except ConfluenceError:
                raise UnreachableError() from None
        return ProjectConfluenceOut(link=None, suggestion=suggestion)

    async def link(self, uid: str, project_key: str, data: LinkInput) -> ConfluenceLinkOut:
        connection_id, client = await self._client(uid)
        async with client:
            try:
                space = await client.space_by_key(data.space_key)
                suggestion = await self._discover(client, project_key)
            except ConfluenceAuthError:
                raise ConfluenceForbiddenError() from None
            except ConfluenceNotFoundError:
                raise SpaceNotFoundError() from None
            except ConfluenceError:
                raise UnreachableError() from None
        if space is None:
            raise SpaceNotFoundError()
        source: LinkSource = (
            suggestion.source
            if suggestion is not None and suggestion.space.key == space.key
            else "manual"
        )
        doc = {
            "connectionId": connection_id,
            "spaceId": space.id,
            "spaceKey": space.key,
            "spaceName": space.name,
            "spaceUrl": space.url,
            "source": source,
            "linkedAt": self._clock(),
        }
        await in_thread(self._store.set, uid, project_key, doc)
        return _link_out(doc)

    async def unlink(self, uid: str, project_key: str) -> None:
        await in_thread(self._store.delete, uid, project_key)

    async def spaces(self, uid: str, query: str = "") -> list[ConfluenceSpaceOut]:
        _, client = await self._client(uid)
        async with client:
            try:
                spaces = await client.list_spaces()
            except ConfluenceAuthError:
                raise ConfluenceForbiddenError() from None
            except ConfluenceNotFoundError:
                raise ConfluenceForbiddenError() from None
            except ConfluenceError:
                raise UnreachableError() from None
        q = query.strip().lower()
        matches = [s for s in spaces if not q or q in s.name.lower() or q in s.key.lower()]
        matches.sort(key=lambda s: s.name.lower())
        return [_space_out(s) for s in matches[:MAX_SPACES_OUT]]

    async def reader_for(
        self, uid: str, project_key: str, connection_id: str
    ) -> tuple[ConfluenceReaderAdapter, ConfluenceClient] | None:
        """Leitor do espaço vinculado para o turno do chat; `None` sem vínculo, vínculo de outra
        conexão ou sem acesso (F19-RF-09). O chamador fecha o cliente."""
        doc = await in_thread(self._store.get, uid, project_key)
        if not doc or doc.get("connectionId") != connection_id:
            return None
        client = await self._connections.confluence_client_for(uid, connection_id)
        space = ConfluenceSpace(
            id=str(doc["spaceId"]),
            key=str(doc["spaceKey"]),
            name=str(doc["spaceName"]),
            url=str(doc["spaceUrl"]),
        )
        return ConfluenceReaderAdapter(client, space, uid), client
