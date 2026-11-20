"""Dublês para os testes do agente e do chat (F05): Jira simulado, armazenamento e roteiros."""

import copy
import json
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from app.agent.tools.context import (
    ActionKind,
    Issue,
    IssueNotFoundError,
    JiraToolError,
    Project,
    ProposedAction,
    ToolContext,
)
from app.integrations.jira.client import JiraClient
from app.services.jira_connections import JiraConnection

SITE = "https://sandbox-teste.atlassian.net"
NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def issue(key: str, summary: str = "Resumo", **kw: Any) -> Issue:
    base: dict[str, Any] = {
        "key": key,
        "summary": summary,
        "issue_type": "Story",
        "status": "To Do",
        "priority": "Medium",
        "labels": (),
        "parent_key": None,
        "description_markdown": "",
        "url": f"{SITE}/browse/{key}",
    }
    return Issue(**(base | kw))


class FakeJiraReader:
    def __init__(
        self, projects: list[Project] | None = None, issues: list[Issue] | None = None
    ) -> None:
        self.projects = projects if projects is not None else [Project("ABC", "Loja")]
        self.issues = {i.key: i for i in issues or []}
        self.searches: list[tuple[str, int]] = []
        self.fail: JiraToolError | None = None

    async def list_projects(self) -> list[Project]:
        if self.fail:
            raise self.fail
        return list(self.projects)

    async def get_issue(self, key: str) -> Issue:
        if key not in self.issues:
            raise IssueNotFoundError(key)
        return self.issues[key]

    async def search(self, jql: str, limit: int) -> list[Issue]:
        self.searches.append((jql, limit))
        return list(self.issues.values())[:limit]


@dataclass
class MemorySink:
    actions: list[dict[str, Any]] = field(default_factory=list)

    async def propose(
        self,
        kind: ActionKind,
        payload: dict[str, Any],
        readiness: dict[str, Any],
        labels: list[str],
        preview: dict[str, Any],
    ) -> ProposedAction:
        action_id = f"act-{len(self.actions) + 1}"
        self.actions.append(
            {
                "id": action_id,
                "kind": kind,
                "payload": payload,
                "readiness": readiness,
                "labels": labels,
                "preview": preview,
            }
        )
        return ProposedAction(action_id, kind, preview)


def tool_config(jira: FakeJiraReader | None, sink: MemorySink | None = None) -> RunnableConfig:
    ctx = ToolContext("uid-alice", "conv-1", jira, sink or MemorySink())
    return {"configurable": {"ctx": ctx}}


def call(name: str, args: dict[str, Any], call_id: str = "call-1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def last_tool_result(messages: list[BaseMessage]) -> str:
    tool = next(m for m in reversed(messages) if isinstance(m, ToolMessage))
    return str(tool.content)


class MemoryChatStore:
    """Mesma interface do `ConversationRepository`, em memória e isolada por `uid`."""

    def __init__(self) -> None:
        self.conversations: dict[str, dict[str, dict[str, Any]]] = {}
        self.messages: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self.actions: dict[str, list[dict[str, Any]]] = {}
        self.usage: dict[tuple[str, str], dict[str, int]] = {}
        self.months: dict[str, int] = {}
        self.issues: dict[str, dict[str, dict[str, Any]]] = {}
        self._next = 0
        self._lock = threading.Lock()

    def _id(self, prefix: str) -> str:
        self._next += 1
        return f"{prefix}-{self._next}"

    def create_conversation(self, uid: str, data: dict[str, Any]) -> str:
        cid = self._id("conv")
        self.conversations.setdefault(uid, {})[cid] = copy.deepcopy(data)
        return cid

    def get_conversation(self, uid: str, conversation_id: str) -> dict[str, Any] | None:
        doc = self.conversations.get(uid, {}).get(conversation_id)
        return None if doc is None else {"id": conversation_id, **copy.deepcopy(doc)}

    def update_conversation(self, uid: str, conversation_id: str, data: dict[str, Any]) -> None:
        self.conversations[uid][conversation_id].update(copy.deepcopy(data))

    # ---- F07: gestão de conversas
    def list_conversations(
        self, uid: str, limit: int, after: tuple[datetime, str] | None
    ) -> list[dict[str, Any]]:
        def key(item: tuple[str, dict[str, Any]]) -> tuple[datetime, str]:
            cid, doc = item
            return doc.get("updatedAt") or doc["createdAt"], cid

        ordered = sorted(self.conversations.get(uid, {}).items(), key=key, reverse=True)
        if after is not None:
            ordered = [i for i in ordered if key(i) < after]
        return [{"id": cid, **copy.deepcopy(doc)} for cid, doc in ordered[:limit]]

    def set_title_if_auto(self, uid: str, conversation_id: str, title: str) -> bool:
        doc = self.conversations.get(uid, {}).get(conversation_id)
        if doc is None or doc.get("titleSource") == "user":
            return False
        doc.update({"title": title, "titleSource": "auto"})
        return True

    def delete_conversation(self, uid: str, conversation_id: str) -> None:
        for record in self.issues.get(uid, {}).values():
            if record.get("conversationId") == conversation_id:
                record["conversationId"] = None  # F10-RT-03
        self.conversations.get(uid, {}).pop(conversation_id, None)
        self.messages.pop((uid, conversation_id), None)
        self.actions[uid] = [
            a for a in self.actions.get(uid, []) if a["conversationId"] != conversation_id
        ]

    def list_messages_before(
        self, uid: str, conversation_id: str, before_seq: int | None, limit: int
    ) -> list[dict[str, Any]]:
        docs = sorted(
            self.messages.get((uid, conversation_id), []), key=lambda d: d["seq"], reverse=True
        )
        if before_seq is not None:
            docs = [d for d in docs if d["seq"] < before_seq]
        return copy.deepcopy(docs[:limit])

    def add_message(self, uid: str, conversation_id: str, data: dict[str, Any]) -> str:
        mid = self._id("msg")
        self.messages.setdefault((uid, conversation_id), []).append({"id": mid, **data})
        conv = self.conversations[uid][conversation_id]
        conv["messageCount"] = conv.get("messageCount", 0) + 1
        conv["updatedAt"] = data["createdAt"]  # mesmo lote no Firestore (F07-RT-04)
        return mid

    def list_messages(self, uid: str, conversation_id: str, limit: int) -> list[dict[str, Any]]:
        docs = sorted(self.messages.get((uid, conversation_id), []), key=lambda d: d["seq"])
        return copy.deepcopy(docs[-limit:])

    def create_action(self, uid: str, data: dict[str, Any]) -> str:
        aid = self._id("act")
        self.actions.setdefault(uid, []).append({"id": aid, **copy.deepcopy(data)})
        return aid

    # ---- ActionStore (F06): mesma interface do ActionRepository
    def _action(self, uid: str, action_id: str) -> dict[str, Any] | None:
        return next((a for a in self.actions.get(uid, []) if a["id"] == action_id), None)

    def get_action(self, uid: str, action_id: str) -> dict[str, Any] | None:
        return copy.deepcopy(self._action(uid, action_id))

    def list_actions(self, uid: str, conversation_id: str) -> list[dict[str, Any]]:
        docs = [a for a in self.actions.get(uid, []) if a["conversationId"] == conversation_id]
        return copy.deepcopy(sorted(docs, key=lambda d: d["createdAt"]))

    def transition(
        self,
        uid: str,
        action_id: str,
        decide: Callable[[dict[str, Any] | None], dict[str, Any] | None],
    ) -> dict[str, Any] | None:
        with self._lock:  # o equivalente à transação do Firestore
            doc = self._action(uid, action_id)
            change = decide(copy.deepcopy(doc))
            if doc is None:
                return None
            if change:
                doc.update(copy.deepcopy(change))
            return copy.deepcopy(doc)

    def update_action(self, uid: str, action_id: str, data: dict[str, Any]) -> None:
        doc = self._action(uid, action_id)
        assert doc is not None
        doc.update(copy.deepcopy(data))

    def complete_action(
        self,
        uid: str,
        action_id: str,
        change: dict[str, Any],
        issue_key: str,
        issue: dict[str, Any],
        first_time: dict[str, Any],
    ) -> None:
        with self._lock:  # uma transação no Firestore
            self.update_action(uid, action_id, change)
            issues = self.issues.setdefault(uid, {})
            record = issues.get(issue_key)
            if record is None:
                issues[issue_key] = copy.deepcopy({**first_time, **issue})
            else:
                record.update(copy.deepcopy(issue))

    # ---- F10: histórico de issues
    def get_issue(self, uid: str, key: str) -> dict[str, Any] | None:
        doc = self.issues.get(uid, {}).get(key)
        return None if doc is None else {"key": key, **copy.deepcopy(doc)}

    def list_issues(
        self,
        uid: str,
        limit: int,
        after: tuple[Any, str] | None,
        since: Any | None,
        until: Any | None,
    ) -> list[dict[str, Any]]:
        items = sorted(
            self.issues.get(uid, {}).items(), key=lambda i: (i[1]["createdAt"], i[0]), reverse=True
        )
        if since is not None:
            items = [i for i in items if i[1]["createdAt"] >= since]
        if until is not None:
            items = [i for i in items if i[1]["createdAt"] < until]
        if after is not None:
            items = [i for i in items if (i[1]["createdAt"], i[0]) < after]
        return [{"key": k, **copy.deepcopy(d)} for k, d in items[:limit]]

    def conversation_titles(self, uid: str, ids: list[str]) -> dict[str, str]:
        convs = self.conversations.get(uid, {})
        return {i: str(convs[i].get("title") or "") for i in ids if i in convs}

    def add_system_message(self, uid: str, conversation_id: str, data: dict[str, Any]) -> str:
        conv = self.conversations.get(uid, {}).get(conversation_id)
        if conv is None:  # conversa excluída enquanto o Jira gravava
            return ""
        seq = conv.get("messageCount", 0) + 1
        return self.add_message(uid, conversation_id, {**data, "role": "system", "seq": seq})

    def add_usage(self, uid: str, day: str, input_tokens: int, output_tokens: int) -> None:
        doc = self.usage.setdefault((uid, day), {})
        doc.setdefault("inputTokens", 0)
        doc.setdefault("outputTokens", 0)
        doc["inputTokens"] += input_tokens
        doc["outputTokens"] += output_tokens

    # ---- F11: cota e rate limit (mesma interface do UsageRepository)
    def update_usage(
        self,
        uid: str,
        day: str,
        decide: Callable[[dict[str, Any]], tuple[dict[str, Any] | None, Any]],
    ) -> Any:
        with self._lock:  # a transação do Firestore
            current = copy.deepcopy(self.usage.get((uid, day), {}))
            change, result = decide(current)
            if change:
                self.usage.setdefault((uid, day), {}).update(copy.deepcopy(change))
            return result

    def usage_days(self, uid: str, days: list[str]) -> dict[str, dict[str, Any]]:
        return {d: copy.deepcopy(self.usage[(uid, d)]) for d in days if (uid, d) in self.usage}

    # ---- F12: teto mensal do beta (mesma interface do UsageRepository)
    def month_tokens(self, month: str) -> int:
        return self.months.get(month, 0)

    def add_month_tokens(self, month: str, tokens: int) -> None:
        with self._lock:
            self.months[month] = self.months.get(month, 0) + tokens


JiraHandler = Callable[[httpx.Request], httpx.Response]

ISSUE_TYPES_EN = [
    {"id": "10001", "name": "Epic", "hierarchyLevel": 1, "subtask": False},
    {"id": "10003", "name": "Task", "hierarchyLevel": 0, "subtask": False},
    {"id": "10004", "name": "Story", "hierarchyLevel": 0, "subtask": False},
    {"id": "10005", "name": "Subtask", "hierarchyLevel": -1, "subtask": True},
]


def issue_types_response(
    request: httpx.Request, types: list[dict[str, Any]]
) -> httpx.Response | None:
    """Responde `createmeta/{projeto}/issuetypes`, que a execução consulta antes de criar."""
    if request.method == "GET" and request.url.path.endswith("/issuetypes"):
        return httpx.Response(200, json={"issueTypes": types})
    return None


def jira_handler(projects: list[dict[str, Any]] | None = None) -> JiraHandler:
    """Jira mínimo: lista projetos, recusa escrita (o teste falha se o agente tentar escrever)."""
    values = projects if projects is not None else [{"key": "ABC", "name": "Loja"}]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method != "GET" and not request.url.path.endswith("/search/jql"):
            raise AssertionError(f"escrita no Jira durante o chat: {request.method} {request.url}")
        if request.url.path == "/rest/api/3/project/search":
            return httpx.Response(200, json={"values": values})
        if request.url.path == "/rest/api/3/search/jql":
            return httpx.Response(200, json={"issues": []})
        return httpx.Response(404, json={})

    return handler


class FakeJiraService:
    """Substitui o `JiraConnectionService`: uma conexão ok (ou nenhuma) e o Jira simulado."""

    def __init__(self, connected: bool = True, handler: JiraHandler | None = None) -> None:
        self.connected = connected
        self.handler = handler or jira_handler()
        self.invalidated: list[str] = []
        self.requests: list[httpx.Request] = []

    async def list(self, uid: str) -> list[JiraConnection]:
        if not self.connected:
            return []
        return [
            JiraConnection(
                id="conn-1",
                site_url=SITE,
                email="po@teste.dev",
                account_name="PO",
                token_hint="9876",
                status="ok",
                last_validated_at=NOW,
            )
        ]

    async def client_for(self, uid: str, connection_id: str) -> JiraClient:
        def recording(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return self.handler(request)

        return JiraClient(SITE, "po@teste.dev", "x" * 12, transport=httpx.MockTransport(recording))

    async def mark_invalid(self, uid: str, connection_id: str) -> None:
        self.invalidated.append(connection_id)


def args_json(message: AIMessage) -> str:
    return json.dumps([c["args"] for c in message.tool_calls], ensure_ascii=False)
