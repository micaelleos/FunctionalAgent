"""Conversor Markdown ⇄ ADF (F05-RT-05) e ADF do renderizador da spec."""

from typing import Any

import pytest

from app.agent.spec.adf import adf_to_markdown, inline_to_adf, markdown_to_adf
from app.agent.spec.parse import parse_issue
from app.agent.spec.render import to_adf
from tests.spec_fixtures import payments_epic, pix_story

pytestmark = pytest.mark.req("F05-RT-05")


def _types(doc: dict[str, Any]) -> list[str]:
    return [n["type"] for n in doc["content"]]


def test_titulos_paragrafos_listas_codigo_e_tabela() -> None:
    doc = markdown_to_adf(
        "# Título\n\nTexto **forte**, *itálico*, ~~riscado~~ e `code`.\n\n"
        "- um\n- dois\n\n1. primeiro\n2. segundo\n\n```python\nx = 1\n```\n\n"
        "| Campo | Tipo |\n|---|---|\n| id | int |\n\n> citação\n\n---\n"
    )

    assert doc["type"] == "doc"
    assert doc["version"] == 1
    assert _types(doc) == [
        "heading",
        "paragraph",
        "bulletList",
        "orderedList",
        "codeBlock",
        "table",
        "blockquote",
        "rule",
    ]
    marks = [n.get("marks", [{}])[0].get("type") for n in doc["content"][1]["content"]]
    assert marks == [None, "strong", None, "em", None, "strike", None, "code", None]
    assert doc["content"][4] == {
        "type": "codeBlock",
        "attrs": {"language": "python"},
        "content": [{"type": "text", "text": "x = 1"}],
    }
    header, row = doc["content"][5]["content"]
    assert header["content"][0]["type"] == "tableHeader"
    assert row["content"][1]["content"][0]["content"][0]["text"] == "int"


def test_link_seguro_vira_marca_e_esquema_inseguro_fica_texto() -> None:
    safe = inline_to_adf("[docs](https://example.com/a)")
    unsafe = inline_to_adf("[x](javascript:alert(1))")

    assert safe == [
        {
            "type": "text",
            "text": "docs",
            "marks": [{"type": "link", "attrs": {"href": "https://example.com/a"}}],
        }
    ]
    assert all("link" not in str(n.get("marks", "")) for n in unsafe)


def test_lista_aninhada_e_quebra_de_linha() -> None:
    doc = markdown_to_adf("- pai\n  - filho\n\nlinha 1  \nlinha 2")
    item = doc["content"][0]["content"][0]

    assert [c["type"] for c in item["content"]] == ["paragraph", "bulletList"]
    assert {"type": "hardBreak"} in doc["content"][1]["content"]


def test_adf_para_markdown_cobre_marcas_listas_e_tabela() -> None:
    md = (
        "## Seção\n\n- **a** e `b`\n- [c](https://x.dev)\n\n1. um\n\n```sh\nls\n```\n\n"
        "| h |\n|---|\n| v |"
    )
    assert adf_to_markdown(markdown_to_adf(md)) == md


def test_adf_vazio_ou_invalido_vira_texto_vazio() -> None:
    assert adf_to_markdown(None) == ""
    assert adf_to_markdown({"type": "doc", "content": []}) == ""


def test_spec_renderizada_tem_codigo_inline_como_marca() -> None:
    adf = to_adf(pix_story())
    context = next(n for n in adf["content"] if n["type"] == "bulletList")
    first = context["content"][0]["content"][0]["content"]

    assert {"type": "text", "text": "PaymentMethod.CARD", "marks": [{"type": "code"}]} in first


@pytest.mark.req("F05-RF-12")
def test_ida_e_volta_pelo_jira_preserva_a_spec() -> None:
    story, epic = pix_story(), payments_epic()

    assert parse_issue(story.title, "Story", adf_to_markdown(to_adf(story))) == story
    assert parse_issue(epic.title, "Epic", adf_to_markdown(to_adf(epic))) == epic
