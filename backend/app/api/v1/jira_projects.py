"""Projetos do Jira do usuário: `/api/v1/jira/projects` (F09)."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, JiraProjects
from app.services.jira_projects import JiraProjectList

router = APIRouter(prefix="/api/v1/jira/projects", tags=["jira"])


@router.get(
    "",
    response_model=JiraProjectList,
    summary="Projetos visíveis para a conta do Jira, com issues abertas e total (cache de 5 min)",
)
async def list_projects(
    user: CurrentUser, service: JiraProjects, refresh: bool = False
) -> JiraProjectList:
    return await service.projects(user.uid, refresh=refresh)
