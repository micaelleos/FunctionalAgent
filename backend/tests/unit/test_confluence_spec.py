"""`references` na AgentReadySpec e o prompt v2 da metodologia (F19-RF-05, F19-RF-06, F19-RT-09)."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.agent.graph import system_prompt
from app.agent.spec.parse import parse_issue
from app.agent.spec.readiness import evaluate
from app.agent.spec.render import REFERENCES, to_markdown
from app.agent.spec.schema import WorkItemSpec, spec_hash
from tests.confluence_fake import WIKI
from tests.spec_fixtures import pix_story_data

RULES = {"title": "Regras de negócio", "url": f"{WIKI}/spaces/SCRUM/pages/101"}


def _story(**extra: object) -> WorkItemSpec:
    return WorkItemSpec.model_validate(pix_story_data() | extra)


@pytest.mark.req("F19-RF-06")
def test_referencias_renderizam_voltam_no_parse_e_mudam_o_hash() -> None:
    spec = _story(references=[RULES])
    markdown = to_markdown(spec)

    assert f"## {REFERENCES}\n- [Regras de negócio]({RULES['url']})" in markdown
    back = parse_issue(spec.title, "Story", markdown)
    assert [r.model_dump() for r in back.references] == [RULES]
    assert spec_hash(spec) != spec_hash(_story())
    assert REFERENCES not in to_markdown(_story())


@pytest.mark.req("F19-RF-06")
def test_referencia_precisa_de_https_e_tem_limite() -> None:
    with pytest.raises(ValidationError):
        _story(references=[{"title": "x", "url": "javascript:alert(1)"}])
    with pytest.raises(ValidationError):
        _story(references=[RULES] * 11)


@pytest.mark.req("F19-RF-06")
def test_links_das_referencias_nao_contam_como_dependencia_externa() -> None:
    # P-10 avisa quando o corpo depende de link/documento; "Referências" é só complemento.
    plain = {r.id: r.passed for r in evaluate(_story()).results}
    with_refs = {r.id: r.passed for r in evaluate(_story(references=[RULES])).results}
    assert with_refs == plain


@pytest.mark.req("F19-RF-05")
@pytest.mark.req("F19-RF-08")
def test_prompt_v2_tem_as_fases_e_o_confluence_e_v1_continua_padrao() -> None:
    v2 = system_prompt("v2", today=date(2026, 11, 20), jira_connected=True)
    for phase in ("Descobrir", "Esclarecer", "Especificar", "Verificar", "Propor", "Convergir"):
        assert f"**{phase}" in v2
    assert "ler_pagina_confluence" in v2
    assert "`conflicts`" in v2
    assert "`references`" in v2
    assert '<dados_confluence confiavel="nao">' in v2
    v1 = system_prompt("v1", today=date(2026, 11, 20), jira_connected=True)
    assert "Confluence" not in v1
