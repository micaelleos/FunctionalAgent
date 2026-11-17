"""Grafo LangGraph com LLM roteirizado (T004): ferramentas, propostas, limite e prompt."""

from datetime import date
from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai._function_utils import convert_to_genai_function_declarations

from app.agent.fake_llm import ScriptedChatModel
from app.agent.graph import JIRA_MISSING, AgentState, build_agent, system_prompt
from app.agent.tools.jira_tools import TOOLS
from app.agent.tools.schemas import model_tool_specs
from tests.chat_fakes import FakeJiraReader, MemorySink, call, last_tool_result, tool_config
from tests.spec_fixtures import pix_story_data


async def _run(llm: ScriptedChatModel, config: Any, max_iterations: int = 8) -> dict[str, Any]:
    agent = build_agent(llm, TOOLS, max_iterations=max_iterations)
    state: AgentState = {"messages": [HumanMessage("oi")], "iterations": 0, "limit_reached": False}
    result: dict[str, Any] = await agent.ainvoke(state, config)
    return result


@pytest.mark.req("F05-RF-04")
async def test_modelo_chama_ferramenta_de_proposta_e_responde_sem_escrever() -> None:
    sink = MemorySink()
    llm = ScriptedChatModel(
        responses=[
            call("listar_projetos", {}),
            call("propor_criacao_issue", {"project_key": "ABC", "spec": pix_story_data()}, "c2"),
            AIMessage("Proposta pronta: confirme no cartão."),
        ]
    )
    result = await _run(llm, tool_config(FakeJiraReader(), sink))

    assert [a["kind"] for a in sink.actions] == ["create_issue"]
    assert result["messages"][-1].content == "Proposta pronta: confirme no cartão."
    assert result["iterations"] == 2
    assert "aguardando confirmação" in last_tool_result(result["messages"])
    assert "propor_criacao_issue" in llm.bound_tools


async def test_argumento_invalido_volta_ao_modelo_como_erro_de_ferramenta() -> None:
    bad = pix_story_data(acceptance_criteria=[{"id": "X", "kind": "erro", "title": "t"}])
    llm = ScriptedChatModel(
        responses=[
            call("propor_criacao_issue", {"project_key": "ABC", "spec": bad}),
            AIMessage("Corrigi."),
        ]
    )
    result = await _run(llm, tool_config(FakeJiraReader()))
    tool_msg = next(m for m in result["messages"] if isinstance(m, ToolMessage))

    assert tool_msg.status == "error"
    assert "pattern" in str(tool_msg.content)


@pytest.mark.req("F05-RT-03")
async def test_limite_de_8_iteracoes_por_turno() -> None:
    llm = ScriptedChatModel(responses=[call("listar_projetos", {}, f"c{i}") for i in range(20)])
    result = await _run(llm, tool_config(FakeJiraReader()))

    assert result["iterations"] == 8
    assert result["limit_reached"] is True
    assert len(llm.calls) == 9  # 8 rodadas com ferramenta + a chamada que excedeu


@pytest.mark.req("F05-RT-01")
async def test_contexto_vem_da_configuracao_e_nao_vaza_entre_execucoes() -> None:
    sink_a, sink_b = MemorySink(), MemorySink()
    for sink in (sink_a, sink_b):
        llm = ScriptedChatModel(
            responses=[
                call("propor_criacao_issue", {"project_key": "ABC", "spec": pix_story_data()}),
                AIMessage("ok"),
            ]
        )
        await _run(llm, tool_config(FakeJiraReader(), sink))

    assert len(sink_a.actions) == len(sink_b.actions) == 1


def test_esquemas_para_o_gemini_sem_referencias_e_com_objetos() -> None:
    specs = model_tool_specs(TOOLS)

    assert "$ref" not in str(specs)
    assert "$defs" not in str(specs)
    [tool] = convert_to_genai_function_declarations(specs)
    declarations = {d.name: d for d in tool.function_declarations or []}
    spec_param = declarations["propor_criacao_issue"].parameters.properties["spec"]  # type: ignore[union-attr,index]
    criteria = spec_param.properties["acceptance_criteria"]  # type: ignore[index]
    assert spec_param.type == "OBJECT"
    assert criteria.items.properties["kind"].enum == ["principal", "alternativo", "erro", "borda"]  # type: ignore[union-attr,index]
    assert set(declarations) == {t.name for t in TOOLS}


@pytest.mark.req("F05-RF-09")
@pytest.mark.req("F05-RF-10")
@pytest.mark.req("F05-RF-11")
@pytest.mark.req("F05-RT-08")
def test_prompt_v1_cobre_perguntar_dividir_human_only_e_dados_nao_confiaveis() -> None:
    prompt = system_prompt("v1", today=date(2026, 11, 16), jira_connected=False)

    assert "Data de hoje: 2026-11-16" in prompt
    assert JIRA_MISSING in prompt
    assert "Perguntar antes de inventar" in prompt
    assert "no máximo 8 critérios de aceite" in prompt
    assert "human_only: true" in prompt
    assert '<dados_jira confiavel="nao">' in prompt
    assert "{" not in prompt


def test_prompt_vai_como_mensagem_de_sistema() -> None:
    seen: list[list[BaseMessage]] = []

    def capture(messages: Any) -> AIMessage:
        seen.append(list(messages))
        return AIMessage("ok")

    llm = ScriptedChatModel(responses=[capture])
    agent = build_agent(llm, TOOLS)
    prompt = SystemMessage(system_prompt("v1", today=date(2026, 1, 1), jira_connected=True))

    import asyncio

    asyncio.run(
        agent.ainvoke(
            {"messages": [prompt, HumanMessage("oi")], "iterations": 0, "limit_reached": False},
            tool_config(None),
        )
    )
    assert isinstance(seen[0][0], SystemMessage)


@pytest.mark.req("F05-RT-03")
async def test_rodadas_de_correcao_nao_gastam_o_limite_mas_tem_teto() -> None:
    # Cenário sem "Dado": a ferramenta devolve para correção (REVIEW_PREFIX) sem criar a ação.
    broken = dict(pix_story_data()["acceptance_criteria"][0], given=[])
    bad = pix_story_data(acceptance_criteria=[broken])
    sink = MemorySink()
    fixes = [
        call("propor_criacao_issue", {"project_key": "ABC", "spec": bad}, f"r{i}") for i in range(3)
    ]
    reads = [call("listar_projetos", {}, f"c{i}") for i in range(7)]
    llm = ScriptedChatModel(responses=[*fixes, *reads, AIMessage("Pronto.")])

    result = await _run(llm, tool_config(FakeJiraReader(), sink))

    assert (result["iterations"], result["reviews"]) == (7, 3)
    assert result["limit_reached"] is False  # 7 + 3 rodadas passariam de 8 se contassem juntas

    endless = ScriptedChatModel(
        responses=[
            call("propor_criacao_issue", {"project_key": "ABC", "spec": bad}, f"x{i}")
            for i in range(20)
        ]
    )
    looped = await _run(endless, tool_config(FakeJiraReader(), MemorySink()))
    assert (looped["reviews"], looped["limit_reached"]) == (8, True)
    assert sink.actions == []
