"""Contexto de cada execução do agente, injetado por `RunnableConfig["configurable"]["ctx"]`.

Nada aqui é global: o serviço de chat monta um `ToolContext` por requisição, com o Jira do usuário
(ou nenhum) e o destino das ações propostas (F05-RT-01). O agente não conhece Firestore nem HTTP:
recebe interfaces (`JiraReader`, `ActionSink`) que o serviço implementa.
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from langchain_core.runnables import RunnableConfig


@dataclass(frozen=True)
class Project:
    key: str
    name: str


@dataclass(frozen=True)
class Issue:
    key: str
    summary: str
    issue_type: str
    status: str
    priority: str | None
    labels: tuple[str, ...]
    parent_key: str | None
    description_markdown: str
    url: str


# Início das respostas em que a ferramenta devolve a proposta ao modelo para correção, sem criar a
# ação (Gherkin incompleto, prontidão, termo sensível). O grafo conta essas rodadas à parte.
REVIEW_PREFIX = "Proposta não criada"


class JiraToolError(Exception):
    """Falha ao consultar o Jira; a mensagem é segura para o modelo e para o usuário."""


class IssueNotFoundError(JiraToolError):
    pass


class JiraReader(Protocol):
    async def list_projects(self) -> list[Project]: ...
    async def get_issue(self, key: str) -> Issue: ...
    async def search(self, jql: str, limit: int) -> list[Issue]: ...


ActionKind = Literal["create_issue", "update_issue"]


@dataclass(frozen=True)
class ProposedAction:
    id: str
    kind: ActionKind
    preview: dict[str, Any]


class ActionSink(Protocol):
    """Guarda a ação proposta (`pending_actions`) e devolve o id; não escreve no Jira (ADR-003)."""

    async def propose(
        self,
        kind: ActionKind,
        payload: dict[str, Any],
        readiness: dict[str, Any],
        labels: list[str],
        preview: dict[str, Any],
    ) -> ProposedAction: ...


@dataclass
class ToolContext:
    uid: str
    conversation_id: str
    jira: JiraReader | None
    actions: ActionSink
    proposed: list[ProposedAction] = field(default_factory=list)
    # Memória do turno (ex.: lista de projetos), descartada no fim da requisição.
    turn_cache: dict[str, Any] = field(default_factory=dict)


def tool_context(config: RunnableConfig) -> ToolContext:
    ctx = (config.get("configurable") or {}).get("ctx")
    if not isinstance(ctx, ToolContext):
        raise RuntimeError("ToolContext ausente na execução do agente")
    return ctx
