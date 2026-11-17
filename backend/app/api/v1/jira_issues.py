"""Histórico de issues do SpecFlow: `/api/v1/jira/issues` (F10)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, JiraIssues
from app.services.jira_issues import (
    AgentPrompt,
    IssuePage,
    Readiness,
    StatusOut,
    StatusRequest,
)

router = APIRouter(prefix="/api/v1/jira/issues", tags=["jira"])


@router.get("", response_model=IssuePage, summary="Issues criadas/atualizadas pelo SpecFlow")
async def list_issues(
    user: CurrentUser,
    service: JiraIssues,
    project: Annotated[str | None, Query(max_length=20)] = None,
    issue_type: Annotated[str | None, Query(alias="type", max_length=40)] = None,
    readiness: Readiness | None = None,
    since: Annotated[datetime | None, Query(alias="from")] = None,
    until: Annotated[datetime | None, Query(alias="to")] = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 25,
) -> IssuePage:
    return await service.issues(
        user.uid,
        project=project,
        issue_type=issue_type,
        readiness=readiness,
        since=since,
        until=until,
        cursor=cursor,
        limit=limit,
    )


@router.post("/status", response_model=StatusOut, summary="Status atual no Jira (até 50 chaves)")
async def issue_statuses(user: CurrentUser, service: JiraIssues, body: StatusRequest) -> StatusOut:
    return await service.statuses(user.uid, body.keys)


@router.get(
    "/{key}/agent-prompt",
    response_model=AgentPrompt,
    summary="Texto da spec para colar no agente de código",
)
async def agent_prompt(user: CurrentUser, service: JiraIssues, key: str) -> AgentPrompt:
    return await service.agent_prompt(user.uid, key)
