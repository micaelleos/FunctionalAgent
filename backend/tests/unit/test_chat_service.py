"""Serviço de chat com LLM roteirizado (F05-RF-01/02/07/08, RT-01, RT-03, RT-07, RT-10)."""

import asyncio
from typing import Any, cast

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from app.agent.fake_llm import ScriptedChatModel
from app.core.config import Settings
from app.services.chat import ChatService, ConversationNotFoundError, history_window
from app.services.chat_events import CHAT_EVENT
from app.services.jira_connections import JiraConnectionService
from tests.chat_fakes import NOW, SITE, FakeJiraService, MemoryChatStore, call
from tests.spec_fixtures import pix_story_data


def _settings(**kw: Any) -> Settings:
    return Settings(env="test", **kw)


def _service(
    llm: ScriptedChatModel,
    store: MemoryChatStore | None = None,
    jira: FakeJiraService | None = None,
    **settings: Any,
) -> tuple[ChatService, MemoryChatStore, FakeJiraService]:
    store = store or MemoryChatStore()
    jira = jira or FakeJiraService()
    service = ChatService(
        store, cast(JiraConnectionService, jira), llm, _settings(**settings), clock=lambda: NOW
    )
    return service, store, jira


async def _turn(
    service: ChatService, text: str, uid: str = "uid-alice", conversation: str = "new"
) -> tuple[str, list[BaseModel]]:
    cid, events = await service.open_turn(uid, conversation, text)
    return cid, [e async for e in events]


def _kinds(events: list[BaseModel]) -> list[str]:
    return [str(getattr(e, "event")) for e in events]  # noqa: B009


@pytest.mark.req("F05-RF-01")
async def test_resposta_em_tokens_seguida_de_message_saved_e_done() -> None:
    service, store, _ = _service(ScriptedChatModel(responses=[AIMessage("Olá! Eu escrevo specs.")]))
    cid, events = await _turn(service, "Olá, o que você faz?")

    assert _kinds(events) == ["token"] * 4 + ["message_saved", "done"]
    assert "".join(getattr(e, "text", "") for e in events) == "Olá! Eu escrevo specs."
    for event in events:
        CHAT_EVENT.validate_python(event.model_dump())
    saved = store.messages[("uid-alice", cid)]
    assert [(m["role"], m["seq"]) for m in saved] == [("user", 1), ("assistant", 2)]
    assert saved[1]["content"] == "Olá! Eu escrevo specs."


@pytest.mark.req("F05-RF-02")
async def test_segundo_turno_recebe_o_historico_da_mesma_conversa() -> None:
    llm = ScriptedChatModel(responses=[AIMessage("Anotado."), AIMessage("Zeta.")])
    service, _, _ = _service(llm)
    cid, _ = await _turn(service, "Meu produto se chama Zeta")
    await _turn(service, "Qual o nome do meu produto?", conversation=cid)

    second = llm.calls[1]
    assert isinstance(second[0], SystemMessage)
    assert [m.content for m in second[1:]] == [
        "Meu produto se chama Zeta",
        "Anotado.",
        "Qual o nome do meu produto?",
    ]


@pytest.mark.req("F05-RT-01")
async def test_dois_usuarios_em_paralelo_sem_cruzamento() -> None:
    store = MemoryChatStore()

    def answer(messages: Any) -> AIMessage:
        last = [m for m in messages if isinstance(m, HumanMessage)]
        return AIMessage(f"vi {len(last)} mensagem(ns): {last[-1].content}")

    async def user(uid: str, secret: str) -> tuple[str, str]:
        llm = ScriptedChatModel(responses=[answer, answer])
        service, _, _ = _service(llm, store)
        cid, _ = await _turn(service, f"segredo {secret}", uid)
        _, events = await _turn(service, "qual o segredo?", uid, cid)
        seen = " ".join(str(m.content) for m in llm.calls[1])
        return seen, "".join(getattr(e, "text", "") for e in events)

    (seen_a, _), (seen_b, _) = await asyncio.gather(user("uid-a", "AAA"), user("uid-b", "BBB"))

    assert "AAA" in seen_a
    assert "BBB" not in seen_a
    assert "BBB" in seen_b
    assert "AAA" not in seen_b


async def test_conversa_de_outro_usuario_nao_e_encontrada() -> None:
    service, _, _ = _service(ScriptedChatModel(responses=[AIMessage("oi")]))
    cid, _ = await _turn(service, "oi", "uid-a")

    with pytest.raises(ConversationNotFoundError):
        await service.open_turn("uid-b", cid, "posso ver?")


@pytest.mark.req("F05-RF-07")
@pytest.mark.req("F05-RF-04")
async def test_eventos_de_ferramenta_e_acao_proposta_sem_escrever_no_jira() -> None:
    llm = ScriptedChatModel(
        responses=[
            call("listar_projetos", {}),
            call("propor_criacao_issue", {"project_key": "ABC", "spec": pix_story_data()}, "c2"),
            AIMessage("Confirme no cartão."),
        ]
    )
    service, store, jira = _service(llm)
    cid, events = await _turn(service, "Crie a story do Pix no ABC")

    kinds = _kinds(events)
    assert kinds[:4] == ["tool_start", "tool_end", "tool_start", "tool_end"]
    assert kinds[4] == "action_proposed"
    proposed = events[4]
    assert getattr(proposed, "kind") == "create_issue"  # noqa: B009
    assert getattr(proposed, "preview")["readiness"]["ready"] is True  # noqa: B009
    assert getattr(events[0], "summary") == "Consultando projetos no Jira…"  # noqa: B009
    [action] = store.actions["uid-alice"]
    assert action["status"] == "pending"
    assert action["conversationId"] == cid
    assert (action["expiresAt"] - action["createdAt"]).total_seconds() == 24 * 3600
    assert len(action["payloadHash"]) == 64
    assert (action["connectionId"], action["siteUrl"]) == ("conn-1", SITE)  # F06: onde escrever
    assert {r.method for r in jira.requests} == {"GET"}
    roles = [m["role"] for m in store.messages[("uid-alice", cid)]]
    assert roles == ["user", "tool", "tool", "assistant"]
    assert "[Ação proposta act-" in store.messages[("uid-alice", cid)][-1]["content"]


@pytest.mark.req("F05-RF-08")
async def test_sem_conexao_jira_o_prompt_avisa_e_nao_ha_cliente() -> None:
    llm = ScriptedChatModel(responses=[AIMessage("Conecte o Jira em Configurações.")])
    service, _, jira = _service(llm, jira=FakeJiraService(connected=False))
    await _turn(service, "Envie ao Jira")

    assert "NÃO tem conexão com o Jira" in str(llm.calls[0][0].content)
    assert jira.requests == []


@pytest.mark.req("F05-RT-03")
async def test_limite_de_ferramentas_vira_evento_de_erro_amigavel() -> None:
    llm = ScriptedChatModel(responses=[call("listar_projetos", {}, f"c{i}") for i in range(20)])
    service, _, _ = _service(llm, agent_max_iterations=2)
    _, events = await _turn(service, "loop")

    error = next(e for e in events if getattr(e, "event") == "error")  # noqa: B009
    assert getattr(error, "code") == "tool-limit"  # noqa: B009
    assert _kinds(events)[-2:] == ["message_saved", "done"]


@pytest.mark.req("F05-RT-03")
async def test_timeout_do_turno() -> None:
    async def slow(messages: Any) -> AIMessage:
        await asyncio.sleep(1)
        return AIMessage("tarde")  # pragma: no cover

    class Slow(ScriptedChatModel):
        async def _agenerate(self, *args: Any, **kwargs: Any) -> Any:
            await asyncio.sleep(1)

        async def _astream(self, *args: Any, **kwargs: Any) -> Any:
            await asyncio.sleep(1)
            yield  # pragma: no cover

    service, _, _ = _service(Slow(responses=[]), agent_turn_timeout_s=0.05)
    _, events = await _turn(service, "oi")

    assert getattr(events[0], "code") == "turn-timeout"  # noqa: B009


async def test_falha_do_modelo_vira_llm_unavailable() -> None:
    def boom(messages: Any) -> AIMessage:
        raise RuntimeError("503 do Vertex")

    service, _, _ = _service(ScriptedChatModel(responses=[boom]))
    _, events = await _turn(service, "oi")

    assert getattr(events[0], "code") == "llm-unavailable"  # noqa: B009
    assert _kinds(events) == ["error", "message_saved", "done"]


@pytest.mark.req("F05-RT-10")
async def test_uso_de_tokens_e_custo_por_turno() -> None:
    llm = ScriptedChatModel(
        responses=[
            AIMessage(
                "oi",
                usage_metadata={
                    "input_tokens": 1_000_000,
                    "output_tokens": 100_000,
                    "total_tokens": 1_100_000,
                },
            )
        ]
    )
    service, store, _ = _service(llm)
    _, events = await _turn(service, "oi")

    usage = getattr(events[-1], "usage")  # noqa: B009
    assert (usage.input_tokens, usage.output_tokens) == (1_000_000, 100_000)
    assert usage.cost_usd == pytest.approx(0.30 + 0.25)
    assert store.usage[("uid-alice", "2026-11-16")] == {
        "inputTokens": 1_000_000,
        "outputTokens": 100_000,
        "messages": 1,
    }


@pytest.mark.req("F05-RT-07")
def test_janela_mantem_as_recentes_dentro_do_orcamento() -> None:
    docs = [
        {"role": "user" if i % 2 else "assistant", "content": "x" * 400, "seq": i}
        for i in range(1, 11)
    ]
    window = history_window(docs, budget=350, summarized_through=0)

    assert len(window.messages) == 3  # 104 tokens estimados cada
    assert [d["seq"] for d in window.to_summarize] == [1, 2, 3, 4, 5, 6, 7]
    already = history_window(docs, budget=350, summarized_through=7)
    assert already.to_summarize == []


@pytest.mark.req("F05-RT-07")
async def test_acima_do_orcamento_resume_e_persiste_o_resumo() -> None:
    def reply(messages: list[BaseMessage]) -> AIMessage:
        if "Resuma a conversa" in str(messages[0].content):
            return AIMessage("- produto Zeta")
        return AIMessage("ok " + "y" * 200)

    llm = ScriptedChatModel(responses=[reply] * 10)
    service, store, _ = _service(llm, history_token_budget=120)
    cid, _ = await _turn(service, "produto Zeta " + "z" * 200)
    for _ in range(2):
        await _turn(service, "mais " + "w" * 200, conversation=cid)
    await _turn(service, "e agora?", conversation=cid)

    conv = store.conversations["uid-alice"][cid]
    assert conv["summary"] == "- produto Zeta"
    assert conv["summarizedThrough"] >= 1
    final = llm.calls[-1]
    assert any("Resumo das mensagens anteriores" in str(m.content) for m in final)
    assert any("Resuma a conversa" in str(c[0].content) for c in llm.calls)


@pytest.mark.req("F06-RF-03")
async def test_proximo_turno_sabe_que_o_usuario_recusou_a_acao() -> None:
    llm = ScriptedChatModel(
        responses=[
            call("propor_criacao_issue", {"project_key": "ABC", "spec": pix_story_data()}),
            AIMessage("Confirme no cartão."),
            AIMessage("Você recusou a criação."),
        ]
    )
    service, store, _ = _service(llm)
    cid, _ = await _turn(service, "Crie a story do Pix no ABC")
    [action] = store.actions["uid-alice"]
    action["status"] = "rejected"

    await _turn(service, "Por que não foi criado?", conversation=cid)

    [system, *_] = llm.calls[-1]
    assert isinstance(system, SystemMessage)
    assert "## Ações propostas nesta conversa (estado atual)" in str(system.content)
    assert f"- {action['id']}: criar Story" in str(system.content)
    assert "RECUSADA pelo usuário" in str(system.content)
    assert sum(isinstance(m, SystemMessage) for m in llm.calls[-1]) == 1
