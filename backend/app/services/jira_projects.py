"""Projetos Jira do usuário (F09): lista paginada, contagens e cache de 5 min no Firestore."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from pydantic import BaseModel

from app.core.errors import ApiProblemError
from app.integrations.jira.client import JiraAuthError, JiraClient, JiraError, JiraProject
from app.services.jira_connections import JiraConnectionService, UnreachableError

CACHE_TTL = timedelta(minutes=5)
COUNT_CONCURRENCY = 5


class JiraProjectOut(BaseModel):
    id: str
    key: str
    name: str
    type: str
    avatar_url: str | None
    # `None`: o Jira não respondeu a contagem; a tela mostra "—" (F09-RT-04).
    open_issues: int | None
    total_issues: int | None
    url: str


class JiraProjectList(BaseModel):
    items: list[JiraProjectOut]
    fetched_at: datetime


class JiraNotConnectedError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(
            409,
            "jira-not-connected",
            "Jira não conectado",
            "Conecte sua conta do Jira em Configurações.",
        )


class JiraCredentialRejectedError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(
            409,
            "jira-credential-rejected",
            "Credencial do Jira recusada",
            "O Jira recusou o token guardado. Troque o token em Configurações.",
        )


class ProjectCache(Protocol):
    def get_projects(self, uid: str) -> dict[str, Any] | None: ...
    def set_projects(self, uid: str, data: dict[str, Any]) -> None: ...


def open_issues_jql(key: str) -> str:
    return f'project = "{key}" AND statusCategory != Done'


class JiraProjectService:
    def __init__(
        self,
        connections: JiraConnectionService,
        cache: ProjectCache,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._connections = connections
        self._cache = cache
        self._clock = clock or (lambda: datetime.now(UTC))

    async def projects(self, uid: str, *, refresh: bool = False) -> JiraProjectList:
        connections = await self._connections.list(uid)
        if not connections:
            raise JiraNotConnectedError()
        connection = connections[0]  # MVP: uma conexão por usuário (F04)
        now = self._clock()
        if not refresh:
            cached = await asyncio.to_thread(self._cache.get_projects, uid)
            if (
                cached
                and cached.get("connectionId") == connection.id
                and cached.get("siteUrl") == connection.site_url
                and now - cached["fetchedAt"] < CACHE_TTL
            ):
                return JiraProjectList(items=cached["projects"], fetched_at=cached["fetchedAt"])

        async with await self._connections.client_for(uid, connection.id) as jira:
            try:
                projects = await jira.list_projects(insight=True, max_pages=20)
            except JiraAuthError:
                await self._connections.mark_invalid(uid, connection.id)
                raise JiraCredentialRejectedError() from None
            except JiraError:
                raise UnreachableError() from None
            items = await self._with_counts(jira, projects)

        await asyncio.to_thread(
            self._cache.set_projects,
            uid,
            {
                "connectionId": connection.id,
                "siteUrl": connection.site_url,
                "fetchedAt": now,
                "projects": [i.model_dump() for i in items],
            },
        )
        return JiraProjectList(items=items, fetched_at=now)

    async def _with_counts(
        self, jira: JiraClient, projects: list[JiraProject]
    ) -> list[JiraProjectOut]:
        """Abertas por projeto, no máximo 5 ao mesmo tempo; falha vira `None` (F09-RT-04)."""
        limit = asyncio.Semaphore(COUNT_CONCURRENCY)

        async def count(project: JiraProject) -> int | None:
            async with limit:
                try:
                    return await jira.approximate_count(open_issues_jql(project.key))
                except (JiraError, KeyError, ValueError, TypeError):
                    return None

        counts = await asyncio.gather(*(count(p) for p in projects))
        return [
            JiraProjectOut(
                id=p.id,
                key=p.key,
                name=p.name,
                type=p.type,
                avatar_url=p.avatar_url,
                open_issues=open_,
                total_issues=p.total_issues,
                url=f"{jira.site_url}/browse/{p.key}",
            )
            for p, open_ in zip(projects, counts, strict=True)
        ]
