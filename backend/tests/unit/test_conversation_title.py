"""Título automático (F07-RF-04, F07-RT-05): em paralelo ao 1º turno; o do usuário fica."""

import asyncio
from typing import Any, cast

import pytest
from langchain_core.messages import AIMessage, BaseMessage

from app.agent.fake_llm import ScriptedChatModel
from app.core.config import Settings
from app.services.chat import ChatService
from app.services.conversation_title import clean_title, provisional_title
from app.services.conversations import ConversationService
from app.services.jira_connections import JiraConnectionService
from tests.chat_fakes import NOW, FakeJiraService, MemoryChatStore

pytestmark = pytest.mark.req("F07-RF-04")
UID = "uid-alice"


def _chat(
    store: MemoryChatStore, title: ScriptedChatModel, agent: list[Any] | None = None
) -> tuple[ChatService, ScriptedChatModel]:
    llm = ScriptedChatModel(responses=agent or [AIMessage("Vamos especificar o checkout.")])
    service = ChatService(
        store,
        cast(JiraConnectionService, FakeJiraService()),
        llm,
        Settings(env="test"),
        clock=lambda: NOW,
        title_llm=title,
    )
    return service, llm


async def _send(
    service: ChatService, text: str, conversation: str = "new"
) -> tuple[str, list[Any]]:
    cid, events = await service.open_turn(UID, conversation, text)
    return cid, [e async for e in events]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Checkout com Pix", "Checkout com Pix"),
        ('"Checkout com Pix."', "Checkout com Pix"),
        ("Título: **Checkout com Pix**\n\nOutra linha", "Checkout com Pix"),
        ("  \n", None),
        ("x" * 80, "x" * 59 + "…"),
    ],
)
def test_titulo_limpo(raw: str, expected: str | None) -> None:
    assert clean_title(raw) == expected


def test_titulo_provisorio_e_a_mensagem_truncada() -> None:
    assert provisional_title("Crie   a story\ndo checkout") == "Crie a story do checkout"
    assert len(provisional_title("palavra " * 30)) == 60


async def test_primeiro_turno_gera_titulo_antes_do_done_e_conta_os_tokens() -> None:
    store = MemoryChatStore()
    title_llm = ScriptedChatModel(responses=[AIMessage("Checkout com Pix")])
    service, _ = _chat(store, title_llm)

    cid, events = await _send(service, "Quero especificar o checkout com Pix")

    assert store.conversations[UID][cid]["title"] == "Checkout com Pix"
    assert "Quero especificar o checkout com Pix" in str(title_llm.calls[0][0].content)
    done = events[-1]
    assert done.usage.input_tokens == 200  # agente + título (100 cada no LLM roteirizado)


async def test_titulo_roda_em_paralelo_aos_tokens_do_agente() -> None:
    store = MemoryChatStore()
    order: list[str] = []
    release = asyncio.Event()

    async def slow_title(messages: list[BaseMessage]) -> AIMessage:
        order.append("título começou")
        await release.wait()
        return AIMessage("Checkout")

    class SlowTitle(ScriptedChatModel):
        async def ainvoke(self, messages: Any, *args: Any, **kwargs: Any) -> AIMessage:  # type: ignore[override]
            return await slow_title(messages)

    def agent(messages: list[BaseMessage]) -> AIMessage:
        order.append("agente respondeu")
        release.set()
        return AIMessage("Resposta")

    service, _ = _chat(store, SlowTitle(responses=[]), agent=[agent])

    cid, _ = await _send(service, "checkout")

    assert order == ["título começou", "agente respondeu"]
    assert store.conversations[UID][cid]["title"] == "Checkout"


async def test_so_o_primeiro_turno_gera_titulo() -> None:
    store = MemoryChatStore()
    title_llm = ScriptedChatModel(responses=[AIMessage("Checkout")])
    service, _ = _chat(store, title_llm, agent=[AIMessage("a"), AIMessage("b")])

    cid, _ = await _send(service, "checkout")
    await _send(service, "e o login?", conversation=cid)

    assert len(title_llm.calls) == 1
    assert store.conversations[UID][cid]["title"] == "Checkout"


async def test_titulo_renomeado_nao_e_sobrescrito() -> None:
    store = MemoryChatStore()
    conversations = ConversationService(store, clock=lambda: NOW)
    created = await conversations.create(UID, None, None)

    async def rename_meanwhile(messages: list[BaseMessage]) -> AIMessage:
        await conversations.update(UID, created.id, {"title": "Meu nome"})
        return AIMessage("Gerado")

    class Renaming(ScriptedChatModel):
        async def ainvoke(self, messages: Any, *args: Any, **kwargs: Any) -> AIMessage:  # type: ignore[override]
            return await rename_meanwhile(messages)

    service, _ = _chat(store, Renaming(responses=[]))

    await _send(service, "checkout", conversation=created.id)

    assert store.conversations[UID][created.id]["title"] == "Meu nome"


async def test_criada_com_titulo_nao_gera_outro() -> None:
    store = MemoryChatStore()
    created = await ConversationService(store, clock=lambda: NOW).create(UID, "Checkout v2", None)
    title_llm = ScriptedChatModel(responses=[])
    service, _ = _chat(store, title_llm)

    await _send(service, "começar", conversation=created.id)

    assert title_llm.calls == []
    assert store.conversations[UID][created.id]["title"] == "Checkout v2"


async def test_criada_vazia_ganha_titulo_provisorio_e_depois_o_gerado() -> None:
    store = MemoryChatStore()
    created = await ConversationService(store, clock=lambda: NOW).create(UID, None, "SCRUM")
    service, _ = _chat(store, ScriptedChatModel(responses=[AIMessage("")]))

    await _send(service, "Story de checkout com Pix", conversation=created.id)

    # Resposta vazia do modelo: fica o provisório.
    assert store.conversations[UID][created.id]["title"] == "Story de checkout com Pix"


async def test_falha_no_titulo_nao_derruba_o_turno() -> None:
    store = MemoryChatStore()

    def boom(messages: list[BaseMessage]) -> AIMessage:
        raise RuntimeError("cota")

    service, _ = _chat(store, ScriptedChatModel(responses=[boom]))

    cid, events = await _send(service, "Checkout com Pix")

    assert [getattr(e, "event") for e in events][-2:] == ["message_saved", "done"]  # noqa: B009
    assert store.conversations[UID][cid]["title"] == "Checkout com Pix"
