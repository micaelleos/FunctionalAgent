"""Avaliar a prontidão de uma issue existente (F05-RF-12, RA-25)."""

import json

import pytest

from app.agent.spec.parse import parse_issue
from app.agent.spec.readiness import evaluate
from app.agent.spec.render import to_markdown
from app.agent.spec.schema import WorkItemSpec
from app.agent.tools.jira_tools import avaliar_prontidao
from tests.chat_fakes import FakeJiraReader, issue, tool_config
from tests.spec_fixtures import pix_story

pytestmark = pytest.mark.req("F05-RF-12")


def _payload(out: str) -> dict[str, object]:
    body = out[out.index("\n") + 1 : out.index("</dados_jira>")]
    data: dict[str, object] = json.loads(body)
    return data


async def test_issue_criada_pelo_specflow_esta_pronta() -> None:
    spec = pix_story()
    jira = FakeJiraReader(
        issues=[issue("ABC-1", spec.title, description_markdown=to_markdown(spec))]
    )

    data = _payload(await avaliar_prontidao.ainvoke({"key": "ABC-1"}, tool_config(jira)))

    assert data["prontidao"] == "pronta para agente de código (todas as regras passam)"
    assert data["regras_que_faltam"] == []


async def test_issue_escrita_a_mao_lista_o_que_falta_e_devolve_a_spec_lida() -> None:
    handmade = (
        "Precisamos melhorar o login, deixar mais rápido.\n\nVer documento em https://wiki.x/login"
    )
    jira = FakeJiraReader(issues=[issue("ABC-2", "Login", description_markdown=handmade)])

    data = _payload(await avaliar_prontidao.ainvoke({"key": "ABC-2"}, tool_config(jira)))
    missing = {r["id"] for r in data["regras_que_faltam"]}  # type: ignore[attr-defined]

    assert str(data["prontidao"]).startswith("NÃO pronta")
    assert {"P-01", "P-02", "P-03", "P-04", "P-05", "P-06", "P-08", "P-10"} <= missing
    assert data["spec_atual"]["context"][0].startswith("Precisamos")  # type: ignore[index]


def test_leitor_tolera_criterios_fora_do_padrao_e_secoes_desconhecidas() -> None:
    md = (
        "## Objetivo\nFazer X\n\n## Critérios de aceite\nDado algo solto\n\n"
        "**CA-01 (erro) Falha**\nDado A\nE B\nQuando C\nEntão D\n\n## Notas\ntexto livre"
    )
    spec = parse_issue("Permitir algo bem definido aqui", "Task", md)

    assert spec.type == "task"
    assert spec.objective.startswith("Fazer X")
    assert isinstance(spec, WorkItemSpec)
    [criterion] = spec.acceptance_criteria
    assert (criterion.given, criterion.when, criterion.then) == (["A", "B"], ["C"], ["D"])
    assert not evaluate(spec).ready


async def test_issue_inexistente() -> None:
    out = await avaliar_prontidao.ainvoke({"key": "ABC-9"}, tool_config(FakeJiraReader()))
    assert "não existe" in out
