"""Adaptador `ConfluenceReader` (F19-RT-02, F19-RT-03, F19-RT-12)."""

import logging

import httpx
import pytest
import respx

from app.agent.tools.context import ConfluenceToolError
from app.integrations.confluence.client import ConfluenceClient, ConfluenceSpace
from app.services.confluence_reader import ConfluenceReaderAdapter, kind_of
from tests.confluence_fake import RULES_STORAGE, WIKI, page_json, search_json
from tests.jira_fake import EMAIL, SITE, TOKEN

SPACE = ConfluenceSpace("65801", "SCRUM", "Minha equipe", f"{WIKI}/spaces/SCRUM")


async def _no_sleep(_: float) -> None:
    return None


def _reader() -> ConfluenceReaderAdapter:
    return ConfluenceReaderAdapter(
        ConfluenceClient(SITE, EMAIL, TOKEN, sleep=_no_sleep), SPACE, "uid-alice"
    )


@pytest.mark.req("F19-RT-03")
@respx.mock
async def test_indice_e_busca_sempre_no_espaco_vinculado() -> None:
    route = respx.get(f"{WIKI}/rest/api/search").mock(
        return_value=httpx.Response(
            200,
            json=search_json(
                ("9", "ADR-001 — Banco", []),
                ("101", "Regras de negócio", ["specflow-tipo-regras"]),
                ("102", "Constituição", []),
            ),
        )
    )
    reader = _reader()
    index = await reader.index()
    await reader.search('x" OR space = "OUTRO', 5)

    assert [(p.title, p.kind) for p in index] == [
        ("Constituição", "constituicao"),
        ("Regras de negócio", "regras"),
        ("ADR-001 — Banco", "adr"),
    ]
    first, second = (c.request.url.params["cql"] for c in route.calls)
    assert first.startswith('space = "SCRUM" AND type = page AND (label in (')
    assert second == 'space = "SCRUM" AND type = page AND text ~ "x\\" OR space = \\"OUTRO"'


@pytest.mark.req("F19-RT-02")
@respx.mock
async def test_pagina_de_outro_espaco_e_recusada() -> None:
    respx.get(f"{WIKI}/api/v2/pages/7").mock(
        return_value=httpx.Response(200, json=page_json("7", "Segredo", "<p>x</p>", "999"))
    )
    with pytest.raises(ConfluenceToolError, match="não é do espaço vinculado"):
        await _reader().page("7")


@pytest.mark.req("F19-RF-09")
@respx.mock
async def test_recusa_vira_erro_seguro_para_o_modelo() -> None:
    respx.get(f"{WIKI}/rest/api/search").mock(return_value=httpx.Response(403))
    with pytest.raises(ConfluenceToolError, match="não tem acesso"):
        await _reader().index()


@pytest.mark.req("F19-RT-12")
@respx.mock
async def test_log_de_leitura_sem_titulo_nem_conteudo(caplog: pytest.LogCaptureFixture) -> None:
    respx.get(f"{WIKI}/api/v2/pages/101").mock(
        return_value=httpx.Response(200, json=page_json("101", "Regras de negócio", RULES_STORAGE))
    )
    with caplog.at_level(logging.INFO, logger="app.confluence"):
        page = await _reader().page("101")

    assert "RN-03" in page.markdown
    [record] = [r for r in caplog.records if r.getMessage() == "confluence_read"]
    fields = record.__dict__["fields"]
    assert fields["event"] == "confluence_read"
    assert fields["tool"] == "page"
    assert fields["pages"] == 1
    assert "uid-alice" not in str(fields)
    assert "Regras" not in str(fields)
    assert "RN-03" not in str(fields)


def test_tipo_pelo_rotulo_ou_titulo() -> None:
    assert kind_of("Qualquer", ("specflow-tipo-glossario",)) == "glossario"
    assert kind_of("Roadmap", ()) == "roadmap"
    assert kind_of("Notas soltas", ()) == ""
