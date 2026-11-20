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


@dataclass(frozen=True)
class DocPage:
    """Página do Confluence vista pelo agente (F19): resumo de busca ou página lida."""

    id: str
    title: str
    url: str
    kind: str = ""  # tipo do modelo da metodologia (rótulo `specflow-tipo-<tipo>`), se houver
    excerpt: str = ""
    markdown: str = ""


@dataclass(frozen=True)
class DocSpace:
    key: str
    name: str
    url: str
    site_url: str  # https://<site>.atlassian.net: referências só deste site (F19-RT-09)


class ConfluenceToolError(Exception):
    """Falha ao consultar o Confluence; a mensagem é segura para o modelo e para o usuário."""


class ConfluenceReader(Protocol):
    """Leitura do espaço vinculado ao projeto da conversa (F19-RT-02); nada fora dele."""

    space: DocSpace

    async def index(self) -> list[DocPage]: ...
    async def search(self, text: str, limit: int) -> list[DocPage]: ...
    async def page(self, page_id: str) -> DocPage: ...


@dataclass(frozen=True)
class PageDraft:
    """Escrita no Confluence pronta para virar ação proposta (F20): `payload` é o que a confirmação
    executa (com hash); `preview` é o que o cartão mostra, com o diff (F20-RT-04)."""

    kind: "ActionKind"
    payload: dict[str, Any]
    preview: dict[str, Any]


class DocsWriter(Protocol):
    """Prepara escritas de páginas no espaço vinculado (F20-RF-02, F20-RF-03); não escreve nada."""

    space: DocSpace

    async def draft_create(
        self, kind: str, title: str, markdown: str, summary: str
    ) -> PageDraft: ...
    async def draft_update(
        self, page_id: str, markdown: str, summary: str, title: str | None
    ) -> PageDraft: ...


class SpaceCreator(Protocol):
    """Prepara a criação do espaço do projeto com o modelo (F20-RF-01); não escreve nada."""

    project_key: str

    async def draft_space(self, project_name: str) -> PageDraft: ...


ActionKind = Literal["create_issue", "update_issue", "create_page", "update_page", "create_space"]


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
    # Espaço do Confluence vinculado ao projeto da conversa (F19); `None` sem vínculo ou sem acesso.
    confluence: ConfluenceReader | None = None
    # Escrita por ação proposta (F20); `None` com a flag desligada ou sem vínculo/espaço livre.
    docs_writer: DocsWriter | None = None
    space_creator: SpaceCreator | None = None
    proposed: list[ProposedAction] = field(default_factory=list)
    # Memória do turno (ex.: lista de projetos), descartada no fim da requisição.
    turn_cache: dict[str, Any] = field(default_factory=dict)


def tool_context(config: RunnableConfig) -> ToolContext:
    ctx = (config.get("configurable") or {}).get("ctx")
    if not isinstance(ctx, ToolContext):
        raise RuntimeError("ToolContext ausente na execução do agente")
    return ctx
