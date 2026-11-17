"""Histórico de issues criadas/atualizadas pelo SpecFlow (F10): lista, status, "Copiar para agente".

Os registros ficam em `users/{uid}/jira_issues/{key}` e são gravados pela F06 junto com a conclusão
da ação. Projeto, tipo e prontidão são filtrados aqui, lendo em lotes: o volume por usuário é
pequeno e assim não há índices compostos para manter (F10-RT-02).
"""

import asyncio
import base64
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel

from app.agent.spec.jira_payload import spec_of
from app.agent.spec.readiness import LABEL_AGENT_READY, LABEL_HUMAN_ONLY
from app.agent.spec.render import to_markdown
from app.core.errors import ApiProblemError
from app.integrations.jira.client import JiraAuthError, JiraError
from app.services.jira_connections import JiraConnectionService, UnreachableError
from app.services.jira_projects import JiraCredentialRejectedError, JiraNotConnectedError

Readiness = Literal["agent_ready", "human_only", "not_ready"]
SCAN_BATCH = 100
MAX_SCAN = 1000
MAX_STATUS_KEYS = 50

AGENT_INSTRUCTION = (
    "Implemente a issue {key} abaixo. Os critérios de aceite são os testes de pronto: escreva um "
    "teste para cada um antes de dar a tarefa por concluída. Respeite o que está fora do escopo."
)


class IssueStore(Protocol):
    def get_issue(self, uid: str, key: str) -> dict[str, Any] | None: ...
    def list_issues(
        self,
        uid: str,
        limit: int,
        after: tuple[Any, str] | None,
        since: Any | None,
        until: Any | None,
    ) -> list[dict[str, Any]]: ...
    def conversation_titles(self, uid: str, ids: list[str]) -> dict[str, str]: ...
    def get_action(self, uid: str, action_id: str) -> dict[str, Any] | None: ...


class IssueOut(BaseModel):
    key: str
    url: str
    project_key: str
    issue_type: str
    summary: str
    readiness: Readiness
    operation: Literal["created", "updated"]
    created_at: datetime
    updated_at: datetime | None
    # `None` quando a conversa foi excluída (F10-RT-03).
    conversation_id: str | None
    conversation_title: str | None
    has_spec: bool


class IssuePage(BaseModel):
    items: list[IssueOut]
    next_cursor: str | None


class IssueStatus(BaseModel):
    name: str
    category: str


class StatusRequest(BaseModel):
    keys: list[str]


class StatusOut(BaseModel):
    # `None`: a issue não existe mais no Jira (ou a conta não a vê).
    statuses: dict[str, IssueStatus | None]


class AgentPrompt(BaseModel):
    key: str
    text: str


class InvalidIssueCursorError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(400, "invalid-cursor", "Cursor de paginação inválido")


class IssueNotFoundError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(404, "issue-not-found", "Issue fora do histórico do SpecFlow")


class SpecUnavailableError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(
            404,
            "spec-unavailable",
            "Sem spec guardada",
            "O SpecFlow só atualizou campos desta issue; não há spec para copiar.",
        )


class TooManyKeysError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(422, "too-many-keys", f"No máximo {MAX_STATUS_KEYS} chaves por vez")


def readiness_of(labels: list[str] | None) -> Readiness:
    values = set(labels or [])
    if LABEL_HUMAN_ONLY in values:
        return "human_only"
    return "agent_ready" if LABEL_AGENT_READY in values else "not_ready"


def _encode(created: datetime, key: str) -> str:
    raw = json.dumps({"c": created.isoformat(), "k": key}).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode(cursor: str | None) -> tuple[datetime, str] | None:
    if cursor is None:
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        return datetime.fromisoformat(str(data["c"])), str(data["k"])
    except (ValueError, KeyError, TypeError) as exc:
        raise InvalidIssueCursorError() from exc


class JiraIssueService:
    def __init__(self, store: IssueStore, connections: JiraConnectionService) -> None:
        self._store = store
        self._connections = connections

    async def _run[T](self, fn: Callable[..., T], *args: Any) -> T:
        return await asyncio.to_thread(fn, *args)

    async def issues(
        self,
        uid: str,
        *,
        project: str | None = None,
        issue_type: str | None = None,
        readiness: Readiness | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        cursor: str | None = None,
        limit: int = 25,
    ) -> IssuePage:
        after = _decode(cursor)

        def wanted(doc: dict[str, Any]) -> bool:
            return (
                (project is None or doc.get("projectKey") == project)
                and (issue_type is None or doc.get("issueType") == issue_type)
                and (readiness is None or readiness_of(doc.get("labels")) == readiness)
            )

        found: list[dict[str, Any]] = []
        scanned, more = 0, False
        while scanned < MAX_SCAN:
            batch = await self._run(self._store.list_issues, uid, SCAN_BATCH, after, since, until)
            scanned += len(batch)
            for doc in batch:
                after = (doc["createdAt"], doc["key"])
                if not wanted(doc):
                    continue
                if len(found) == limit:
                    more = True
                    break
                found.append(doc)
            if more or len(batch) < SCAN_BATCH:
                break
        else:
            more = True  # leu o máximo sem terminar: o cursor continua de onde parou
        if more and found:
            last = found[-1]
            next_cursor: str | None = _encode(last["createdAt"], last["key"])
        elif more:
            next_cursor = _encode(*after) if after else None
        else:
            next_cursor = None

        ids = sorted({d["conversationId"] for d in found if d.get("conversationId")})
        titles = await self._run(self._store.conversation_titles, uid, ids) if ids else {}
        items = [
            IssueOut(
                key=d["key"],
                url=str(d.get("url") or ""),
                project_key=str(d.get("projectKey") or ""),
                issue_type=str(d.get("issueType") or ""),
                summary=str(d.get("summary") or ""),
                readiness=readiness_of(d.get("labels")),
                operation=d.get("operation") or "created",
                created_at=d["createdAt"],
                updated_at=d.get("updatedAt"),
                conversation_id=d.get("conversationId")
                if d.get("conversationId") in titles
                else None,
                conversation_title=titles.get(d.get("conversationId") or ""),
                has_spec=bool(d.get("specActionId") or d.get("actionId")),
            )
            for d in found
        ]
        return IssuePage(items=items, next_cursor=next_cursor)

    async def statuses(self, uid: str, keys: list[str]) -> StatusOut:
        unique = list(dict.fromkeys(k.strip().upper() for k in keys if k.strip()))
        if len(unique) > MAX_STATUS_KEYS:
            raise TooManyKeysError()
        if not unique:
            return StatusOut(statuses={})
        connections = await self._connections.list(uid)
        if not connections:
            raise JiraNotConnectedError()
        connection = connections[0]
        async with await self._connections.client_for(uid, connection.id) as jira:
            try:
                found = await jira.statuses(unique)
            except JiraAuthError:
                await self._connections.mark_invalid(uid, connection.id)
                raise JiraCredentialRejectedError() from None
            except JiraError:
                raise UnreachableError() from None
        return StatusOut(
            statuses={
                k: IssueStatus(name=found[k].name, category=found[k].category)
                if k in found
                else None
                for k in unique
            }
        )

    async def agent_prompt(self, uid: str, key: str) -> AgentPrompt:
        """Texto para colar no agente de código, da spec que o PO confirmou (F10-RF-06)."""
        record = await self._run(self._store.get_issue, uid, key)
        if record is None:
            raise IssueNotFoundError()
        action_id = record.get("specActionId") or record.get("actionId")
        action = await self._run(self._store.get_action, uid, action_id) if action_id else None
        spec = spec_of(action["payload"]) if action else None
        if spec is None:
            raise SpecUnavailableError()
        url = str(record.get("url") or "")
        text = "\n\n".join(
            [
                AGENT_INSTRUCTION.format(key=key),
                f"# {key} · {spec.title}",
                f"Issue no Jira: {url}",
                to_markdown(spec).strip(),
            ]
        )
        return AgentPrompt(key=key, text=text + "\n")
