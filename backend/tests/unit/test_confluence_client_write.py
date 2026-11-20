"""Escrita no Confluence (F20-RT-02): uma tentativa só, versão contra sobrescrita (F20-RF-04)."""

import json

import httpx
import pytest
import respx

from app.integrations.confluence.client import (
    ConfluenceAuthError,
    ConfluenceBadRequestError,
    ConfluenceClient,
    ConfluenceConflictError,
    ConfluenceRateLimitedError,
    ConfluenceUncertainError,
    ConfluenceUnreachableError,
)
from tests.confluence_fake import SPACE, WIKI, spaces
from tests.jira_fake import EMAIL, SITE, TOKEN


async def _no_sleep(_: float) -> None:
    return None


def client() -> ConfluenceClient:
    return ConfluenceClient(SITE, EMAIL, TOKEN, sleep=_no_sleep)


def _created(page_id: str = "900", title: str = "Glossário", version: int = 1) -> dict[str, object]:
    return {
        "id": page_id,
        "title": title,
        "spaceId": "65801",
        "version": {"number": version},
        "_links": {"webui": f"/spaces/SCRUM/pages/{page_id}"},
    }


@pytest.mark.req("F20-RT-02")
@respx.mock
async def test_cria_pagina_com_pai_e_storage() -> None:
    route = respx.post(f"{WIKI}/api/v2/pages").mock(
        return_value=httpx.Response(200, json=_created())
    )
    async with client() as confluence:
        page = await confluence.create_page("65801", "Glossário", "<p>x</p>", parent_id="100")

    body = json.loads(route.calls.last.request.content)
    assert body == {
        "spaceId": "65801",
        "status": "current",
        "title": "Glossário",
        "body": {"representation": "storage", "value": "<p>x</p>"},
        "parentId": "100",
    }
    assert (page.id, page.version, page.url) == ("900", 1, f"{WIKI}/spaces/SCRUM/pages/900")


@pytest.mark.req("F20-RF-04")
@pytest.mark.req("F20-RT-02")
@respx.mock
async def test_atualiza_com_versao_vista_mais_um_e_409_vira_conflito() -> None:
    route = respx.put(f"{WIKI}/api/v2/pages/900").mock(
        side_effect=[httpx.Response(200, json=_created(version=4)), httpx.Response(409, json={})]
    )
    async with client() as confluence:
        page = await confluence.update_page("900", "Glossário", "<p>y</p>", 3, "SpecFlow")
        with pytest.raises(ConfluenceConflictError):
            await confluence.update_page("900", "Glossário", "<p>z</p>", 3)

    first = json.loads(route.calls[0].request.content)
    assert first["version"] == {"number": 4, "message": "SpecFlow"}
    assert page.version == 4
    assert route.call_count == 2  # o 409 não é repetido


@pytest.mark.req("F20-RT-02")
@respx.mock
async def test_escrita_nunca_repete() -> None:
    route = respx.post(f"{WIKI}/api/v2/pages").mock(return_value=httpx.Response(503))
    async with client() as confluence:
        with pytest.raises(ConfluenceUncertainError):
            await confluence.create_page("65801", "T", "<p/>")
    assert route.call_count == 1


@pytest.mark.req("F20-RT-02")
@respx.mock
@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(403), ConfluenceAuthError),
        (httpx.Response(429), ConfluenceRateLimitedError),
        (
            httpx.Response(400, json={"errors": [{"title": "Título já existe"}]}),
            ConfluenceBadRequestError,
        ),
        (httpx.Response(302), ConfluenceUnreachableError),
    ],
)
async def test_erros_da_escrita(response: httpx.Response, error: type[Exception]) -> None:
    respx.post(f"{WIKI}/api/v2/pages").mock(return_value=response)
    async with client() as confluence:
        with pytest.raises(error):
            await confluence.create_page("65801", "T", "<p/>")


@pytest.mark.req("F20-RT-02")
@respx.mock
async def test_timeout_depois_de_enviar_e_incerto_e_sem_conexao_nao() -> None:
    respx.post(f"{WIKI}/api/v2/pages").mock(side_effect=httpx.ReadTimeout("lento"))
    respx.put(f"{WIKI}/api/v2/pages/1").mock(side_effect=httpx.ConnectTimeout("off"))
    async with client() as confluence:
        with pytest.raises(ConfluenceUncertainError):
            await confluence.create_page("65801", "T", "<p/>")
        with pytest.raises(ConfluenceUnreachableError):
            await confluence.update_page("1", "T", "<p/>", 1)


@pytest.mark.req("F20-RT-02")
@respx.mock
async def test_cria_espaco_pela_v1_e_rotulos() -> None:
    created = respx.post(f"{WIKI}/rest/api/space").mock(return_value=httpx.Response(200, json={}))
    spaces(respx.mock, SPACE)
    labels = respx.post(f"{WIKI}/rest/api/content/900/label").mock(
        return_value=httpx.Response(200, json={})
    )
    async with client() as confluence:
        space = await confluence.create_space("SCRUM", "Scrum — Documentação")
        await confluence.add_labels("900", ["specflow", "specflow-tipo-glossario"])
        await confluence.add_labels("900", [])

    assert json.loads(created.calls.last.request.content) == {
        "key": "SCRUM",
        "name": "Scrum — Documentação",
    }
    assert space.id == "65801"
    assert json.loads(labels.calls.last.request.content) == [
        {"prefix": "global", "name": "specflow"},
        {"prefix": "global", "name": "specflow-tipo-glossario"},
    ]
    assert labels.call_count == 1
