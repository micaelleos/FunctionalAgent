"""Agente legado para o baseline (T001): `prompt_2` e ferramentas com a mesma forma das antigas.

O legado usava GPT e escrevia direto no Jira. Aqui as ferramentas só registram o que teriam feito
(nada sai da máquina além da chamada ao modelo) e o modelo é o mesmo da implementação nova, para
que a comparação meça o prompt e o contrato, não o fornecedor do LLM.
"""

import ast
from pathlib import Path
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from app.agent.tools.context import IssueNotFoundError, tool_context

LEGACY_PROMPT_FILE = (
    Path(__file__).resolve().parents[1] / "legacy" / "src" / "scripts" / "prompt.py"
)


def legacy_prompt() -> str:
    """Lê `prompt_2` do arquivo legado sem importá-lo (o módulo puxa Streamlit)."""
    tree = ast.parse(LEGACY_PROMPT_FILE.read_text("utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "prompt_2":
            return str(ast.literal_eval(node.value))
    raise RuntimeError("prompt_2 não encontrado")


class IssueJira(BaseModel):
    project: str = Field(description="nome do projeto onde será criado o issue")
    title: str = Field(description="Título do issue, em frase resumida com até 4 palavras")
    description: str = Field(description="descrição do issue")
    issuetype: Literal["Task", "Story", "Epic"] = Field(description="Tipo do issue a ser criado")
    priority: Literal["Highest", "High", "Medium", "Low", "Lowest"] = Field(
        default="Medium", description="Prioridade"
    )
    parentKey: str | None = Field(default=None, description="chave do issue pai")  # noqa: N815


def _writes(config: RunnableConfig) -> list[dict[str, Any]]:
    ctx = tool_context(config)
    writes: list[dict[str, Any]] = ctx.turn_cache.setdefault("legacy_writes", [])
    return writes


@tool(args_schema=IssueJira)
async def criar_issue_jira(config: RunnableConfig, **data: Any) -> str:
    """Chame essa função para criar issues no Jira"""
    ctx = tool_context(config)
    if ctx.jira is None:
        return (
            "Aconteceu um erro ao enviar o issue ao Jira. O usuário não configurou as credenciais"
        )
    _writes(config).append({"kind": "create_issue", **data})
    return f"Issue criado: {data['project']}-{100 + len(_writes(config))}"


@tool
async def get_all_projects(config: RunnableConfig) -> str:
    """Chame essa ferramenta para consultar os projetos no Jira"""
    ctx = tool_context(config)
    if ctx.jira is None:
        return "O usuário não configurou as credenciais da sua conta do Jira"
    return str([{"key": p.key, "name": p.name} for p in await ctx.jira.list_projects()])


@tool
async def consultar_issue(issue_key: str, config: RunnableConfig) -> str:
    """Chame essa ferramenta para consultar issues no Jira"""
    ctx = tool_context(config)
    if ctx.jira is None:
        return "O usuário não configurou as credenciais da sua conta do Jira"
    try:
        issue = await ctx.jira.get_issue(issue_key)
    except IssueNotFoundError:
        return "Erro: issue não encontrado"
    return str(
        {"key": issue.key, "summary": issue.summary, "description": issue.description_markdown}
    )


class AtualizaIssue(BaseModel):
    issue_key: str
    fields: dict[str, str] = Field(description="campos a atualizar")


@tool(args_schema=AtualizaIssue)
async def atualizar_issue_jira(
    issue_key: str, fields: dict[str, str], config: RunnableConfig
) -> str:
    """Chame essa ferramenta para atualizar issues no Jira"""
    _writes(config).append({"kind": "update_issue", "issue_key": issue_key, **fields})
    return "Issue atualizado"


@tool
async def consultar_jql_query(jql: str, config: RunnableConfig) -> str:
    """Faça qualquer consulta no Jira a partir de uma query JQL."""
    ctx = tool_context(config)
    if ctx.jira is None:
        return "O usuário não configurou as credenciais da sua conta do Jira"
    return str([{"key": i.key, "summary": i.summary} for i in await ctx.jira.search(jql, 50)])


LEGACY_TOOLS: list[BaseTool] = [
    criar_issue_jira,
    get_all_projects,
    consultar_issue,
    atualizar_issue_jira,
    consultar_jql_query,
]
