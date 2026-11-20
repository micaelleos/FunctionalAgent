"""Cliente do Confluence (F19-RT-01, F19-RT-03, F19-RT-06) contra um Confluence simulado (respx)."""

import httpx
import pytest
import respx

from app.integrations.confluence.client import (
    ConfluenceAuthError,
    ConfluenceClient,
    ConfluenceNotFoundError,
    ConfluenceUnreachableError,
    cql_string,
)
from app.integrations.confluence.markdown import TRUNCATED, storage_to_markdown
from app.integrations.jira.urls import InvalidSiteUrlError
from tests.confluence_fake import RULES_STORAGE, SPACE, WIKI, page_json, search_json, spaces
from tests.jira_fake import EMAIL, SITE, TOKEN


async def _no_sleep(_: float) -> None:
    return None


def client() -> ConfluenceClient:
    return ConfluenceClient(SITE, EMAIL, TOKEN, sleep=_no_sleep)


@pytest.mark.req("F19-RT-01")
@respx.mock
async def test_espaco_pela_chave_no_mesmo_site_com_basic_auth() -> None:
    route = spaces(respx.mock, SPACE)
    async with client() as confluence:
        space = await confluence.space_by_key("SCRUM")
        missing = await confluence.space_by_key("OUTRO")

    assert space is not None
    assert (space.id, space.key, space.url) == ("65801", "SCRUM", f"{WIKI}/spaces/SCRUM")
    assert missing is None
    assert route.calls.last.request.headers["Authorization"].startswith("Basic ")
    assert str(route.calls.last.request.url).startswith(f"{SITE}/wiki/")


@pytest.mark.req("F19-RT-01")
def test_site_fora_do_atlassian_e_recusado() -> None:
    with pytest.raises(InvalidSiteUrlError):
        ConfluenceClient("https://evil.example.com", EMAIL, TOKEN)


@pytest.mark.req("F19-RT-01")
@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, ConfluenceAuthError),
        (403, ConfluenceAuthError),
        (404, ConfluenceNotFoundError),
        (302, ConfluenceUnreachableError),
    ],
)
@respx.mock
async def test_erros_mapeados_sem_seguir_redirect(status: int, error: type[Exception]) -> None:
    headers = {"Location": "https://outro-host.example.com/roubar"} if status == 302 else {}
    respx.get(f"{WIKI}/api/v2/pages/1").mock(return_value=httpx.Response(status, headers=headers))
    async with client() as confluence:
        with pytest.raises(error):
            await confluence.page("1")
    assert respx.calls.call_count == 1


@pytest.mark.req("F19-RT-01")
@respx.mock
async def test_repete_em_429_e_5xx() -> None:
    route = respx.get(f"{WIKI}/api/v2/pages/7").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "1"}),
            httpx.Response(503),
            httpx.Response(200, json=page_json("7", "Regras de negócio", RULES_STORAGE)),
        ]
    )
    async with client() as confluence:
        page = await confluence.page("7")
    assert route.call_count == 3
    assert (page.title, page.version, page.space_id) == ("Regras de negócio", 3, "65801")


@pytest.mark.req("F19-RT-03")
@respx.mock
async def test_busca_cql_com_rotulos_e_so_paginas() -> None:
    body = search_json(("101", "Regras de negócio", ["specflow", "specflow-tipo-regras"]))
    body["results"].append({"content": {"id": "9", "type": "attachment", "title": "x.png"}})
    route = respx.get(f"{WIKI}/rest/api/search").mock(return_value=httpx.Response(200, json=body))
    async with client() as confluence:
        pages = await confluence.search('space = "SCRUM"', limit=99)

    assert [(p.id, p.labels) for p in pages] == [("101", ("specflow", "specflow-tipo-regras"))]
    assert route.calls.last.request.url.params["limit"] == "25"


@pytest.mark.req("F19-RT-03")
def test_literal_cql_escapa_aspas_e_barras() -> None:
    assert cql_string('a" OR space = "X') == '"a\\" OR space = \\"X"'
    assert cql_string("c:\\x") == '"c: x"'


@pytest.mark.req("F19-RT-01")
async def test_pagina_com_id_invalido_nao_chama_o_confluence() -> None:
    async with client() as confluence:
        with pytest.raises(ConfluenceNotFoundError):
            await confluence.page("../../rest/api/user")


@pytest.mark.req("F19-RT-06")
def test_storage_vira_markdown() -> None:
    storage = (
        "<h2>Regras</h2><p>Texto <strong>forte</strong> e "
        '<a href="https://x.atlassian.net/wiki/a">link</a>.</p>'
        "<ul><li>um</li><li>dois<ul><li>sub</li></ul></li></ul>"
        "<table><tbody><tr><th>ID</th><th>Regra</th></tr>"
        "<tr><td>RN-01</td><td>a | b</td></tr></tbody></table>"
        '<ac:structured-macro ac:name="code"><ac:plain-text-body>x = 1</ac:plain-text-body>'
        "</ac:structured-macro>"
        '<ac:structured-macro ac:name="status"><ac:parameter ac:name="title">Aceita'
        "</ac:parameter></ac:structured-macro>"
        '<ac:structured-macro ac:name="jira"><ac:parameter ac:name="key">S-1</ac:parameter>'
        "</ac:structured-macro>"
        '<ac:structured-macro ac:name="toc"><ac:parameter ac:name="x">1</ac:parameter>'
        "</ac:structured-macro>"
    )
    md = storage_to_markdown(storage)

    assert "## Regras" in md
    assert "Texto **forte** e [link](https://x.atlassian.net/wiki/a)." in md
    assert "- um\n- dois\n  - sub" in md
    assert "| ID | Regra |\n|---|---|\n| RN-01 | a \\| b |" in md
    assert "```\nx = 1\n```" in md
    assert "[status: Aceita]" in md
    assert "[macro: jira]" in md
    assert "S-1" not in md


@pytest.mark.req("F19-RT-04")
def test_pagina_longa_e_truncada() -> None:
    md = storage_to_markdown("<p>" + "palavra " * 3000 + "</p>", limit=100)
    assert md.endswith(TRUNCATED)
    assert len(md) <= 100 + len(TRUNCATED)
