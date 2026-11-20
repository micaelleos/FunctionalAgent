"""Turno de conversa com o agente (F05-RF-01, F05-RF-02, F05-RT-01, F05-RT-03, F05-RT-07, RT-10).

Cada turno: carrega a conversa do usuário → aplica a janela do histórico (com sumarização
persistida) → executa o grafo em streaming → traduz para eventos SSE → grava as mensagens do
usuário, das ferramentas e do assistente e o uso de tokens. Nada fica em memória entre turnos.
"""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    AnyMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from app.agent.graph import Agent, AgentState, build_agent, project_note, system_prompt
from app.agent.spec.jira_payload import payload_hash
from app.agent.tools.confluence_tools import CONFLUENCE_TOOLS, index_note
from app.agent.tools.context import (
    ActionKind,
    ConfluenceReader,
    ConfluenceToolError,
    ProposedAction,
    ToolContext,
)
from app.agent.tools.jira_tools import JIRA_TOOLS, PROGRESS
from app.core.errors import ApiProblemError
from app.core.logging import uid_hash
from app.core.telemetry import in_thread
from app.services.actions import describe, to_out
from app.services.chat_events import (
    ActionProposedEvent,
    DoneEvent,
    ErrorEvent,
    MessageSavedEvent,
    TokenEvent,
    ToolEndEvent,
    ToolStartEvent,
    Usage,
)
from app.services.conversation_title import generate_title, provisional_title
from app.services.jira_connections import JiraConnectionService
from app.services.jira_reader import JiraReaderAdapter
from app.services.usage import UsageService, usage_day

log = logging.getLogger("app.chat")

NEW = "new"
HISTORY_FETCH = 100
ACTION_TTL = timedelta(hours=24)
TOOL_CONTENT_MAX = 4000
TITLE_TIMEOUT_S = 15
SUMMARY_PROMPT = (
    "Resuma a conversa abaixo entre um Product Owner e o assistente SpecFlow em até 12 itens: "
    "decisões, nomes, projetos do Jira, specs em andamento e perguntas pendentes. Só fatos ditos "
    "na conversa. Responda apenas com os itens."
)
NO_DOCS_NOTE = (
    "## Documentação do projeto\n"
    "O projeto desta conversa não tem espaço do Confluence vinculado (ou a conta não tem acesso "
    "a ele). Siga sem a documentação; diga uma única vez na conversa que o vínculo é feito em "
    "Projects, se ajudar."
)
ERRORS = {
    "turn-timeout": "A resposta demorou demais. Tente de novo.",
    "tool-limit": (
        "O agente consultou ferramentas demais neste turno. Reformule ou divida o pedido."
    ),
    "llm-unavailable": "O modelo está indisponível no momento. Tente de novo em instantes.",
    "internal": "Algo deu errado neste turno. Tente de novo.",
}


class ChatStore(Protocol):
    def create_conversation(self, uid: str, data: dict[str, Any]) -> str: ...
    def get_conversation(self, uid: str, conversation_id: str) -> dict[str, Any] | None: ...
    def update_conversation(self, uid: str, conversation_id: str, data: dict[str, Any]) -> None: ...
    def add_message(self, uid: str, conversation_id: str, data: dict[str, Any]) -> str: ...
    def list_messages(self, uid: str, conversation_id: str, limit: int) -> list[dict[str, Any]]: ...
    def create_action(self, uid: str, data: dict[str, Any]) -> str: ...
    def list_actions(self, uid: str, conversation_id: str) -> list[dict[str, Any]]: ...
    def set_title_if_auto(self, uid: str, conversation_id: str, title: str) -> bool: ...
    def add_usage(self, uid: str, day: str, input_tokens: int, output_tokens: int) -> None: ...


class Closable(Protocol):
    async def aclose(self) -> None: ...


class DocsLinks(Protocol):
    """Vínculo projeto ↔ espaço do Confluence (F19); `ConfluenceLinkService` implementa."""

    async def reader_for(
        self, uid: str, project_key: str, connection_id: str
    ) -> tuple[ConfluenceReader, Closable] | None: ...


class ChatSettings(Protocol):
    llm_model: str
    prompt_version: str
    agent_max_iterations: int
    agent_turn_timeout_s: float
    history_token_budget: int
    llm_price_input_per_mtok: float
    llm_price_output_per_mtok: float
    confluence_enabled: bool


class ConversationNotFoundError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(404, "conversation-not-found", "Conversa não encontrada")


def estimate_tokens(text: str) -> int:
    """Estimativa barata (≈ 4 caracteres por token), suficiente para a janela do histórico."""
    return len(text) // 4 + 4


def message_text(content: Any) -> str:
    """Texto de uma mensagem do modelo; o Gemini pode devolver partes (texto, raciocínio…)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text", "")))
        return "".join(parts)
    return ""


@dataclass
class Window:
    messages: list[BaseMessage]
    to_summarize: list[dict[str, Any]]
    # Avisos do SpecFlow depois da última resposta (ex.: "o usuário recusou a ação"): vão junto
    # da mensagem atual do usuário, para o modelo vê-los na ordem em que aconteceram (F06-RF-03).
    pending_events: list[str]


EVENTS_HEADER = "[Avisos do SpecFlow desde a sua última resposta; não foram escritos pelo usuário]"


def with_events(text: str, events: list[str]) -> str:
    if not events:
        return text
    return "\n".join([EVENTS_HEADER, *(f"- {e}" for e in events), "", text])


def history_window(docs: list[dict[str, Any]], budget: int, summarized_through: int) -> Window:
    """Mensagens mais recentes que cabem no orçamento; as que saíram e ainda não estão no resumo
    vão para `to_summarize` (F05-RT-07)."""
    chat = [d for d in docs if d.get("role") in ("user", "assistant", "system")]
    kept: list[dict[str, Any]] = []
    used = 0
    for doc in reversed(chat):
        cost = estimate_tokens(str(doc.get("content", "")))
        if kept and used + cost > budget:
            break
        kept.append(doc)
        used += cost
    kept.reverse()
    first_kept = kept[0]["seq"] if kept else 1 << 30
    dropped = [d for d in chat if d["seq"] < first_kept and d["seq"] > summarized_through]
    messages: list[BaseMessage] = []
    events: list[str] = []
    for doc in kept:
        if doc["role"] == "system":
            events.append(str(doc["content"]))
        elif doc["role"] == "user":
            messages.append(HumanMessage(with_events(doc["content"], events)))
            events = []
        else:
            messages.append(AIMessage(doc["content"]))
    return Window(messages, dropped, events)


def _assistant_content(text: str, actions: list[ProposedAction]) -> str:
    """O que fica no histórico: o texto e uma nota das ações propostas (o modelo as vê depois)."""
    notes = [
        f"[Ação proposta {a.id}: {a.kind} {a.preview.get('summary', '')}"
        f" — aguardando confirmação do usuário]"
        for a in actions
    ]
    return "\n".join([text, *notes]).strip()


_ACTION_STATE = {
    "pending": "aguardando a confirmação do usuário no cartão",
    "executing": "em execução no Jira",
    "expired": "expirou sem confirmação (nada foi escrito)",
    "rejected": "RECUSADA pelo usuário (nada foi escrito no Jira)",
}
MAX_ACTIONS_NOTE = 20


def actions_note(docs: list[dict[str, Any]], now: datetime) -> str:
    """Estado das ações desta conversa, para o agente responder sobre elas (F06-RF-03)."""
    lines = []
    for doc in docs[-MAX_ACTIONS_NOTE:]:
        action = to_out(doc, now)
        if action.status == "done" and action.result:
            verb = "criada" if action.kind == "create_issue" else "atualizada"
            state = (
                f"confirmada pelo usuário; {action.result.issue_key} {verb} ({action.result.url})"
            )
        elif action.status == "failed" and action.error:
            state = f"confirmada, mas falhou no Jira: {action.error.message}"
        else:
            state = _ACTION_STATE[action.status]
        lines.append(f"- {action.id}: {describe(doc)} — {state}")
    if not lines:
        return ""
    return "\n".join(
        [
            "## Ações propostas nesta conversa (estado atual)",
            "Use este estado para responder sobre os cartões (recusada: diga que o usuário "
            "recusou; criada: dê a chave e o link; falhou: explique o erro). Não proponha de novo "
            "uma ação recusada sem o usuário pedir.",
            *lines,
        ]
    )


class FirestoreActionSink:
    """Grava `users/{uid}/pending_actions/{id}` (ADR-003); a execução no Jira é da F06."""

    def __init__(
        self, store: ChatStore, uid: str, conversation_id: str, clock: Callable[[], datetime]
    ) -> None:
        self._store = store
        self._uid = uid
        self._conversation_id = conversation_id
        self._clock = clock
        # Conexão do Jira em uso no turno: a execução (F06) só escreve nela, no mesmo site.
        self.connection_id: str | None = None
        self.site_url: str | None = None

    async def propose(
        self,
        kind: ActionKind,
        payload: dict[str, Any],
        readiness: dict[str, Any],
        labels: list[str],
        preview: dict[str, Any],
    ) -> ProposedAction:
        now = self._clock()
        doc = {
            "kind": kind,
            "payload": payload,
            "payloadHash": payload_hash(payload),
            "readiness": readiness,
            "labels": labels,
            "preview": preview,
            "status": "pending",
            "conversationId": self._conversation_id,
            "connectionId": self.connection_id,
            "siteUrl": self.site_url,
            "createdAt": now,
            "expiresAt": now + ACTION_TTL,
        }
        action_id = await in_thread(self._store.create_action, self._uid, doc)
        log.info(  # métrica de ações propostas (F11-RT-03)
            "action_proposed",
            extra={
                "fields": {
                    "event": "action_proposed",
                    "uid_hash": uid_hash(self._uid),
                    "action_id": action_id,
                    "kind": kind,
                    # Indicador da F19: propostas que citam a documentação do projeto.
                    "references": len((payload.get("spec") or {}).get("references") or []),
                    "conflicts": len(preview.get("conflicts") or []),
                }
            },
        )
        return ProposedAction(action_id, kind, preview)


class _Turn:
    def __init__(self) -> None:
        self.text: list[str] = []
        self.input_tokens = 0
        self.output_tokens = 0
        self.tool_messages: list[ToolMessage] = []
        # `time.monotonic()` do 1º pedaço de texto (latência do 1º token, F11-RT-03).
        self.first_token_at: float | None = None

    def add_usage(self, message: BaseMessage) -> None:
        usage = getattr(message, "usage_metadata", None) or {}
        self.input_tokens += int(usage.get("input_tokens", 0))
        self.output_tokens += int(usage.get("output_tokens", 0))


_agents: dict[tuple[int, int, bool], tuple[BaseChatModel, Agent]] = {}


def shared_agent(llm: BaseChatModel, max_iterations: int, *, docs: bool = False) -> Agent:
    """Grafo compilado uma vez por modelo compartilhado (F11-RT-08).

    Só para modelos que vivem o processo todo (o de `api/deps.py`); guarda o modelo junto para o
    `id` nunca ser reaproveitado por outro objeto.
    """
    key = (id(llm), max_iterations, docs)
    if key not in _agents:
        tools = [*JIRA_TOOLS, *CONFLUENCE_TOOLS] if docs else JIRA_TOOLS
        _agents[key] = (llm, build_agent(llm, tools, max_iterations=max_iterations))
    return _agents[key][1]


class ChatService:
    def __init__(
        self,
        store: ChatStore,
        jira: JiraConnectionService,
        llm: BaseChatModel,
        settings: ChatSettings,
        *,
        tools: list[BaseTool] | None = None,
        clock: Callable[[], datetime] | None = None,
        title_llm: BaseChatModel | None = None,
        usage: UsageService | None = None,
        agent: Agent | None = None,
        docs_agent: Agent | None = None,
        confluence: DocsLinks | None = None,
    ) -> None:
        self._store = store
        # Documentação do projeto no Confluence (F19); `None` ou flag desligada: sem leitura.
        self._confluence = confluence
        # Grafo já compilado e compartilhado (F11-RT-08): compilar custa ~metade da CPU de um turno.
        # O estado vem em cada invocação, então o mesmo grafo serve requisições simultâneas.
        self._agent = agent
        # O mesmo grafo com as ferramentas do Confluence, para turnos com espaço vinculado (F19).
        self._docs_agent = docs_agent
        # Cota diária e rate limit (F11); `None` nos testes que não tratam disso.
        self._usage = usage
        # Título automático (F07-RT-05); `None` desliga (testes com LLM roteirizado).
        self._title_llm = title_llm
        self._jira = jira
        self._llm = llm
        self._settings = settings
        self._tools = tools if tools is not None else JIRA_TOOLS
        self._clock = clock or (lambda: datetime.now(UTC))

    async def _run_sync[T](self, fn: Callable[..., T], *args: Any) -> T:
        return await in_thread(fn, *args)

    async def open_turn(
        self, uid: str, conversation_id: str, text: str
    ) -> tuple[str, AsyncGenerator[BaseModel]]:
        """Valida a conversa e grava a mensagem do usuário antes de começar o streaming, para que
        404 e erros de validação saiam como Problem Details, não como evento."""
        if self._usage is not None:
            # Antes de tudo: mensagem recusada (429) não cria conversa nem chama o modelo.
            await self._usage.reserve(uid)
        now = self._clock()
        if conversation_id == NEW:
            conversation: dict[str, Any] = {
                "title": provisional_title(text),
                "titleSource": "auto",
                "projectKey": None,
                "createdAt": now,
                "updatedAt": now,
                "messageCount": 0,
                "summary": "",
                "summarizedThrough": 0,
            }
            conversation_id = await self._run_sync(
                self._store.create_conversation, uid, conversation
            )
            conversation["id"] = conversation_id
        else:
            found = await self._run_sync(self._store.get_conversation, uid, conversation_id)
            if found is None:
                raise ConversationNotFoundError()
            conversation = found
            if self._is_untitled(conversation):  # criada vazia por POST /conversations (F07)
                title = provisional_title(text)
                await self._run_sync(
                    self._store.update_conversation, uid, conversation_id, {"title": title}
                )
                conversation["title"] = title
        docs = await self._run_sync(self._store.list_messages, uid, conversation_id, HISTORY_FETCH)
        seq = max([int(conversation.get("messageCount", 0)), *(int(d["seq"]) for d in docs)])
        user_doc = {"role": "user", "content": text, "seq": seq + 1, "createdAt": now}
        user_message_id = await self._run_sync(
            self._store.add_message, uid, conversation_id, user_doc
        )
        needs_title = self._title_llm is not None and self._is_untitled(conversation)
        events = self._stream(
            uid, conversation, docs, text, user_message_id, seq + 1, needs_title=needs_title
        )
        return conversation_id, events

    @staticmethod
    def _is_untitled(conversation: dict[str, Any]) -> bool:
        """Sem mensagens e sem título dado pelo usuário: o 1º turno gera o título."""
        return (
            conversation.get("titleSource", "auto") == "auto"
            and int(conversation.get("messageCount", 0)) == 0
        )

    async def _title(
        self, llm: BaseChatModel, uid: str, conversation_id: str, text: str, turn: "_Turn"
    ) -> None:
        """Em paralelo ao agente; erro aqui nunca derruba o turno (fica o título provisório)."""
        try:
            title, response = await generate_title(llm, text)
            turn.add_usage(response)
            if title:
                await self._run_sync(self._store.set_title_if_auto, uid, conversation_id, title)
        except Exception:  # o título é acessório
            log.warning("falha ao gerar o título", extra={"conversation_id": conversation_id})

    async def _jira_reader(
        self, uid: str, sink: FirestoreActionSink
    ) -> tuple[JiraReaderAdapter | None, Any]:
        connections = await self._jira.list(uid)
        usable = next((c for c in connections if c.status == "ok"), None)
        if usable is None:
            return None, None
        client = await self._jira.client_for(uid, usable.id)
        sink.connection_id, sink.site_url = usable.id, client.site_url

        async def on_auth_error() -> None:
            await self._jira.mark_invalid(uid, usable.id)

        return JiraReaderAdapter(client, on_auth_error), client

    def _agent_for(self, *, docs: bool) -> Agent:
        shared = self._docs_agent if docs else self._agent
        if shared is not None:
            return shared
        tools = [*self._tools, *CONFLUENCE_TOOLS] if docs else self._tools
        return build_agent(self._llm, tools, max_iterations=self._settings.agent_max_iterations)

    async def _docs_note(
        self, uid: str, project_key: str | None, sink: FirestoreActionSink, ctx: ToolContext
    ) -> tuple[str, Any]:
        """Fase Descobrir (F19-RF-04): leitor do espaço vinculado e o índice dele para a instrução
        de sistema. Sem vínculo ou sem acesso, o turno segue sem documentação (F19-RF-09)."""
        if (
            self._confluence is None
            or not self._settings.confluence_enabled
            or not project_key
            or sink.connection_id is None
        ):
            return "", None
        found = await self._confluence.reader_for(uid, project_key, sink.connection_id)
        if found is None:
            return NO_DOCS_NOTE, None
        reader, client = found
        try:
            pages = await reader.index()
        except ConfluenceToolError:
            await client.aclose()
            return NO_DOCS_NOTE, None
        ctx.confluence = reader
        return index_note(reader.space, pages), client

    async def _summarize(
        self, uid: str, conversation: dict[str, Any], dropped: list[dict[str, Any]], turn: _Turn
    ) -> str:
        previous = str(conversation.get("summary") or "")
        transcript = "\n".join(f"{d['role']}: {d['content']}" for d in dropped)
        prompt = f"{SUMMARY_PROMPT}\n\nResumo anterior:\n{previous or '(nenhum)'}\n\n{transcript}"
        response = await self._llm.ainvoke([HumanMessage(prompt)])
        turn.add_usage(response)
        summary = message_text(response.content).strip()
        through = int(dropped[-1]["seq"])
        await self._run_sync(
            self._store.update_conversation,
            uid,
            conversation["id"],
            {"summary": summary, "summarizedThrough": through},
        )
        return summary

    async def _stream(
        self,
        uid: str,
        conversation: dict[str, Any],
        docs: list[dict[str, Any]],
        text: str,
        user_message_id: str,
        user_seq: int,
        *,
        needs_title: bool = False,
    ) -> AsyncGenerator[BaseModel]:
        conversation_id = str(conversation["id"])
        started = time.monotonic()
        turn = _Turn()
        titling = (
            asyncio.create_task(self._title(self._title_llm, uid, conversation_id, text, turn))
            if needs_title and self._title_llm is not None
            else None
        )
        error: str | None = None
        reader, client, docs_client = None, None, None
        sink = FirestoreActionSink(self._store, uid, conversation_id, self._clock)
        ctx = ToolContext(uid=uid, conversation_id=conversation_id, jira=None, actions=sink)
        reported = 0
        interrupted, saved = False, False
        try:
            try:
                async with asyncio.timeout(self._settings.agent_turn_timeout_s):
                    reader, client = await self._jira_reader(uid, sink)
                    ctx.jira = reader
                    window = history_window(
                        docs,
                        self._settings.history_token_budget,
                        int(conversation.get("summarizedThrough", 0)),
                    )
                    summary = str(conversation.get("summary") or "")
                    if window.to_summarize:
                        summary = await self._summarize(
                            uid, conversation, window.to_summarize, turn
                        )
                    instructions = [
                        system_prompt(
                            self._settings.prompt_version,
                            today=self._clock().date(),
                            jira_connected=reader is not None,
                        )
                    ]
                    if summary:
                        instructions.append(f"## Resumo das mensagens anteriores\n{summary}")
                    actions = await self._run_sync(self._store.list_actions, uid, conversation_id)
                    if note := actions_note(actions, self._clock()):
                        instructions.append(note)
                    project_key = conversation.get("projectKey")
                    if project_key:
                        instructions.append(project_note(str(project_key)))
                    docs_note, docs_client = await self._docs_note(
                        uid, str(project_key) if project_key else None, sink, ctx
                    )
                    if docs_note:
                        instructions.append(docs_note)
                    # Uma única instrução de sistema: o Gemini só aceita uma, no início.
                    messages: list[BaseMessage] = [
                        SystemMessage("\n\n".join(instructions)),
                        *window.messages,
                        HumanMessage(with_events(text, window.pending_events)),
                    ]
                    agent = self._agent_for(docs=ctx.confluence is not None)
                    state: AgentState = {
                        "messages": cast(list[AnyMessage], messages),
                        "iterations": 0,
                        "limit_reached": False,
                    }
                    config: RunnableConfig = {"configurable": {"ctx": ctx}, "recursion_limit": 100}
                    parts: AsyncIterator[Any] = cast(
                        AsyncIterator[Any],
                        agent.astream(state, config, stream_mode=["messages", "updates"]),
                    )
                    async for mode, chunk in parts:
                        if mode == "messages":
                            message, meta = chunk
                            # Chunks do streaming; sem streaming, vem a mensagem inteira.
                            if meta.get("langgraph_node") == "model" and isinstance(
                                message, AIMessageChunk | AIMessage
                            ):
                                piece = message_text(message.content)
                                if piece:
                                    if turn.first_token_at is None:
                                        turn.first_token_at = time.monotonic()
                                    turn.text.append(piece)
                                    yield TokenEvent(text=piece)
                            continue
                        for node, update in (chunk or {}).items():
                            if not update:
                                continue
                            if update.get("limit_reached"):
                                error = "tool-limit"
                            for msg in update.get("messages", []):
                                if node == "model" and isinstance(msg, AIMessage):
                                    turn.add_usage(msg)
                                    for call in msg.tool_calls:
                                        summary_text = PROGRESS.get(call["name"], "Consultando…")
                                        yield ToolStartEvent(
                                            name=call["name"], summary=summary_text
                                        )
                                elif isinstance(msg, ToolMessage):
                                    turn.tool_messages.append(msg)
                                    done = "Falhou" if msg.status == "error" else "Concluído"
                                    yield ToolEndEvent(name=str(msg.name), summary=done)
                            for action in ctx.proposed[reported:]:
                                yield ActionProposedEvent(
                                    action_id=action.id, kind=action.kind, preview=action.preview
                                )
                            reported = len(ctx.proposed)
            except (asyncio.CancelledError, GeneratorExit):
                interrupted = True
                raise
            except TimeoutError:
                error = "turn-timeout"
            except Exception:
                log.exception(
                    "falha no turno do agente", extra={"conversation_id": conversation_id}
                )
                error = "llm-unavailable"
            finally:
                if client is not None:
                    await client.aclose()
                if docs_client is not None:
                    await docs_client.aclose()
                if titling is not None and interrupted:
                    titling.cancel()
                elif titling is not None:
                    # O título fica pronto antes do `done` (o front relê a lista nesse momento).
                    try:
                        await asyncio.wait_for(titling, TITLE_TIMEOUT_S)
                    except TimeoutError:
                        log.warning(
                            "título não gerado a tempo", extra={"conversation_id": conversation_id}
                        )

            if error:
                yield ErrorEvent.model_validate({"code": error, "message": ERRORS[error]})
            message_id = await self._persist(uid, conversation_id, user_seq, turn, ctx.proposed)
            saved = True
            yield MessageSavedEvent(
                message_id=message_id,
                conversation_id=conversation_id,
                user_message_id=user_message_id,
            )
            usage = await self._record_usage(uid, conversation_id, turn, started, error)
            yield DoneEvent(usage=usage)
        except (asyncio.CancelledError, GeneratorExit):
            # F08-RT-09: o cliente desconectou ("Parar", aba fechada). Grava o que já saiu,
            # marcado, e o uso; o shield impede que o cancelamento corte a gravação.
            if not saved:
                await asyncio.shield(
                    self._save_interrupted(uid, conversation_id, user_seq, turn, ctx, started)
                )
            raise

    async def _save_interrupted(
        self,
        uid: str,
        conversation_id: str,
        user_seq: int,
        turn: _Turn,
        ctx: ToolContext,
        started: float,
    ) -> None:
        try:
            await self._persist(
                uid, conversation_id, user_seq, turn, ctx.proposed, interrupted=True
            )
            await self._record_usage(uid, conversation_id, turn, started, "interrupted")
        except Exception:
            log.exception("falha ao gravar a resposta interrompida")

    async def _persist(
        self,
        uid: str,
        conversation_id: str,
        user_seq: int,
        turn: _Turn,
        actions: list[ProposedAction],
        *,
        interrupted: bool = False,
    ) -> str:
        seq = user_seq
        for tool_msg in turn.tool_messages:
            seq += 1
            await self._run_sync(
                self._store.add_message,
                uid,
                conversation_id,
                {
                    "role": "tool",
                    "name": tool_msg.name,
                    "content": message_text(tool_msg.content)[:TOOL_CONTENT_MAX],
                    "seq": seq,
                    "createdAt": self._clock(),
                },
            )
        content = _assistant_content("".join(turn.text), actions)
        return await self._run_sync(
            self._store.add_message,
            uid,
            conversation_id,
            {
                "role": "assistant",
                "content": content,
                "text": "".join(turn.text),  # o que o usuário viu (histórico da F07)
                "interrupted": interrupted,
                "seq": seq + 1,
                "actions": [{"id": a.id, "kind": a.kind} for a in actions],
                "usage": {"inputTokens": turn.input_tokens, "outputTokens": turn.output_tokens},
                "model": self._settings.llm_model,
                "promptVersion": self._settings.prompt_version,
                "createdAt": self._clock(),
            },
        )

    async def _record_usage(
        self, uid: str, conversation_id: str, turn: _Turn, started: float, error: str | None
    ) -> Usage:
        """Tokens e custo estimado por turno: log estruturado + `users/{uid}/usage/{dia}`."""
        cost = (
            turn.input_tokens * self._settings.llm_price_input_per_mtok
            + turn.output_tokens * self._settings.llm_price_output_per_mtok
        ) / 1_000_000
        usage = Usage(
            input_tokens=turn.input_tokens,
            output_tokens=turn.output_tokens,
            cost_usd=round(cost, 6),
        )
        day = usage_day(self._clock())  # o dia da cota é o de Brasília (F11-RT-05)
        await self._run_sync(self._store.add_usage, uid, day, turn.input_tokens, turn.output_tokens)
        if self._usage is not None:
            await self._usage.record_tokens(turn.input_tokens + turn.output_tokens)
        log.info(
            "chat_turn",
            extra={
                "fields": {
                    "event": "chat_turn",
                    "uid_hash": uid_hash(uid),
                    "conversation_id": conversation_id,
                    "model": self._settings.llm_model,
                    "prompt_version": self._settings.prompt_version,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "cost_usd": usage.cost_usd,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "first_token_ms": (
                        int((turn.first_token_at - started) * 1000)
                        if turn.first_token_at is not None
                        else None
                    ),
                    "error": error,
                }
            },
        )
        return usage
