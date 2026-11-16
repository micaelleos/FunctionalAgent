"""Grafo do agente (ADR-003): `modelo ⇄ ferramentas`, no máximo N iterações de ferramenta por turno.

O grafo é montado por requisição (`build_agent`) e não guarda estado entre turnos: o histórico vem
do serviço de chat e o `ToolContext` chega por `RunnableConfig` (F05-RT-01).
"""

from datetime import date
from functools import cache
from importlib import resources
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from app.agent.tools.schemas import model_tool_specs

JIRA_CONNECTED = "O usuário tem conexão com o Jira."
JIRA_MISSING = (
    "O usuário NÃO tem conexão com o Jira: ajude na documentação e, se ele quiser enviar ao Jira, "
    "oriente a conectar em Configurações → Jira."
)


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    iterations: int
    limit_reached: bool


@cache
def _prompt_template(version: str) -> str:
    return resources.files("app.agent.prompts").joinpath(f"system_{version}.md").read_text("utf-8")


def system_prompt(version: str, *, today: date, jira_connected: bool) -> str:
    return (
        _prompt_template(version)
        .replace("{today}", today.isoformat())
        .replace("{jira_status}", JIRA_CONNECTED if jira_connected else JIRA_MISSING)
    )


def build_agent(
    llm: BaseChatModel, tools: list[BaseTool], *, max_iterations: int = 8
) -> CompiledStateGraph[AgentState, Any, AgentState, AgentState]:
    model = llm.bind_tools(model_tool_specs(tools))

    async def call_model(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        response = await model.ainvoke(state["messages"], config)
        return {"messages": [response]}

    def route(state: AgentState) -> Literal["tools", "__end__"]:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "__end__"

    tool_node = ToolNode(tools, handle_tool_errors=True)

    async def run_tools(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        if state.get("iterations", 0) >= max_iterations:
            # F05-RT-03: para aqui; o serviço avisa o usuário.
            return {"limit_reached": True}
        result = await tool_node.ainvoke(state, config)
        return {**result, "iterations": state.get("iterations", 0) + 1}

    def after_tools(state: AgentState) -> Literal["model", "__end__"]:
        return "__end__" if state.get("limit_reached") else "model"

    graph = StateGraph(AgentState)
    graph.add_node("model", call_model)
    graph.add_node("tools", run_tools)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route)
    graph.add_conditional_edges("tools", after_tools)
    return graph.compile()
