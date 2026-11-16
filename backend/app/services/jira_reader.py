"""Adapta o `JiraClient` do usuário à interface de leitura das ferramentas do agente.

Traduz os tipos e erros da integração para os do agente (as camadas não se importam) e marca a
conexão como inválida quando o Jira recusa o token no meio da conversa (F04-RF-06).
"""

from collections.abc import Awaitable, Callable

from app.agent.spec.adf import adf_to_markdown
from app.agent.tools.context import Issue, IssueNotFoundError, JiraToolError, Project
from app.integrations.jira.client import (
    JiraAuthError,
    JiraBadRequestError,
    JiraClient,
    JiraError,
    JiraIssue,
    JiraNotFoundError,
)

AUTH_MESSAGE = (
    "o Jira recusou a credencial do usuário; peça para ele atualizar o token em "
    "Configurações → Jira"
)


def _issue(issue: JiraIssue) -> Issue:
    return Issue(
        key=issue.key,
        summary=issue.summary,
        issue_type=issue.issue_type,
        status=issue.status,
        priority=issue.priority,
        labels=issue.labels,
        parent_key=issue.parent_key,
        description_markdown=adf_to_markdown(issue.description),
        url=issue.url,
    )


class JiraReaderAdapter:
    def __init__(self, client: JiraClient, on_auth_error: Callable[[], Awaitable[None]]) -> None:
        self._client = client
        self._on_auth_error = on_auth_error
        self.auth_failed = False

    async def _fail(self, exc: JiraError) -> JiraToolError:
        if isinstance(exc, JiraAuthError):
            if not self.auth_failed:
                self.auth_failed = True
                await self._on_auth_error()
            return JiraToolError(AUTH_MESSAGE)
        if isinstance(exc, JiraNotFoundError):
            return IssueNotFoundError(str(exc))
        if isinstance(exc, JiraBadRequestError):
            return JiraToolError(str(exc))
        return JiraToolError("o Jira não respondeu; tente de novo em instantes")

    async def list_projects(self) -> list[Project]:
        try:
            return [Project(p.key, p.name) for p in await self._client.list_projects()]
        except JiraError as exc:
            raise await self._fail(exc) from None

    async def get_issue(self, key: str) -> Issue:
        try:
            return _issue(await self._client.get_issue(key))
        except JiraError as exc:
            raise await self._fail(exc) from None

    async def search(self, jql: str, limit: int) -> list[Issue]:
        try:
            return [_issue(i) for i in await self._client.search(jql, limit)]
        except JiraError as exc:
            raise await self._fail(exc) from None
