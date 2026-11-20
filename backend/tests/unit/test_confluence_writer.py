"""Preparação das páginas e do espaço (F20-RF-01..03, F20-RF-06, F20-RT-03, F20-RT-08)."""

import pytest

from app.agent.tools.context import ConfluenceToolError
from app.integrations.confluence.client import ConfluenceSpace
from app.services.confluence_reader import ConfluenceReaderAdapter
from app.services.confluence_writer import (
    MAX_STORAGE,
    ConfluenceWriterAdapter,
    SpaceCreatorAdapter,
    space_key_for,
)
from tests.confluence_fake import WIKI, FakeWiki

GLOSSARY = "# Glossário — Loja\n\n| Termo | Definição |\n|---|---|\n| Pedido | compra |\n"


def writer(wiki: FakeWiki) -> ConfluenceWriterAdapter:
    space = wiki.spaces.get("SCRUM") or wiki.add_space()
    client = wiki.client()
    linked = ConfluenceSpace(space["id"], "SCRUM", "Minha equipe", f"{WIKI}/spaces/SCRUM")
    return ConfluenceWriterAdapter(client, ConfluenceReaderAdapter(client, linked, "u"), "SCRUM")


@pytest.mark.req("F20-RF-02")
async def test_pagina_nova_vai_sob_o_inicio_com_rotulos_e_diff() -> None:
    wiki = FakeWiki()
    home = wiki.add_space()["homepageId"]
    draft = await writer(wiki).draft_create("glossario", "Glossário", GLOSSARY, "Termo Pedido")

    assert draft.kind == "create_page"
    assert draft.payload["parent_id"] == home
    assert draft.payload["labels"] == ["specflow", "specflow-tipo-glossario"]
    assert draft.payload["storage"].startswith("<h1>Glossário — Loja</h1><table>")
    assert draft.payload["project_key"] == "SCRUM"
    assert [d["change"] for d in draft.preview["diff"]] == ["added"]
    assert draft.preview["parent_title"] == "Início"
    assert wiki.writes == []  # nada escrito na proposta


@pytest.mark.req("F20-RF-02")
async def test_pagina_unica_que_ja_existe_vira_atualizacao() -> None:
    wiki = FakeWiki()
    wiki.add_space()
    page_id = wiki.add_page("Glossário", "<p>x</p>", ["specflow-tipo-glossario"])
    with pytest.raises(ConfluenceToolError, match=f"id {page_id}.*propor_atualizacao_pagina"):
        await writer(wiki).draft_create("glossario", "Glossário 2", GLOSSARY, "Termo Pedido")


@pytest.mark.req("F20-RF-06")
async def test_adr_nova_vai_em_decisoes_com_numero_livre() -> None:
    wiki = FakeWiki()
    wiki.add_space()
    parent = wiki.add_page("Decisões (ADR)", "<p/>", ["specflow-tipo-adr"])
    wiki.add_page("ADR-001 — Postgres", "<p/>", ["specflow-tipo-adr"])
    w = writer(wiki)
    adr = "# ADR-002 — Fila\n\n**Status:** Proposta\n\n## Contexto\nx\n\n## Decisão\ny\n"

    draft = await w.draft_create("adr", "ADR-002 — Fila", adr, "Decisão da fila")
    assert draft.payload["parent_id"] == parent
    with pytest.raises(ConfluenceToolError, match="ADR-001 já existe"):
        await w.draft_create("adr", "ADR-001 — Outra", adr, "Outra decisão")
    with pytest.raises(ConfluenceToolError, match="ADR-001 — <decisão>"):
        await w.draft_create("adr", "Fila", adr, "Sem número")


@pytest.mark.req("F20-RF-03")
async def test_atualizacao_guarda_a_versao_vista_e_o_diff_por_secao() -> None:
    wiki = FakeWiki()
    wiki.add_space()
    page_id = wiki.add_page(
        "Glossário",
        "<h1>Glossário</h1><h2>Termos</h2><p>Pedido: compra</p>",
        ["specflow-tipo-glossario"],
        version=7,
    )
    new = "# Glossário\n\n## Termos\nPedido: compra confirmada\n\n## Novos\nCliente\n"
    draft = await writer(wiki).draft_update(page_id, new, "Cliente e Pedido", None)

    assert draft.kind == "update_page"
    assert (draft.payload["page_id"], draft.payload["version"]) == (page_id, 7)
    assert [(d["section"], d["change"]) for d in draft.preview["diff"]] == [
        ("Termos", "changed"),
        ("Novos", "added"),
    ]
    assert draft.preview["url"].endswith(f"/pages/{page_id}")


@pytest.mark.req("F20-RF-03")
@pytest.mark.req("F20-RF-06")
@pytest.mark.parametrize(
    ("title", "storage", "labels", "error"),
    [
        ("Registro de mudanças", "<p>x</p>", ["specflow-tipo-registro"], "Registro de mudanças"),
        ("Notas soltas", "<p>x</p>", [], "só leitura"),
        (
            "ADR-001 — Postgres",
            "<p><strong>Status:</strong> Aceita</p>",
            ["specflow-tipo-adr"],
            "ADR aceita",
        ),
        ("Glossário", "<p>" + "x" * 9000 + "</p>", ["specflow-tipo-glossario"], "longa demais"),
        ("Glossário", "<h1>Glossário</h1><p>Pedido</p>", ["specflow-tipo-glossario"], "igual"),
    ],
)
async def test_atualizacoes_recusadas(
    title: str, storage: str, labels: list[str], error: str
) -> None:
    wiki = FakeWiki()
    wiki.add_space()
    page_id = wiki.add_page(title, storage, labels)
    with pytest.raises(ConfluenceToolError, match=error):
        await writer(wiki).draft_update(
            page_id, f"# {title}\n\nPedido\n", "Resumo da mudança", None
        )


@pytest.mark.req("F20-RF-03")
async def test_pagina_de_outro_espaco_e_recusada() -> None:
    wiki = FakeWiki()
    wiki.add_space()
    wiki.add_space("OUTRO", "Outro")
    page_id = wiki.add_page("Glossário", "<p>x</p>", ["specflow-tipo-glossario"], key="OUTRO")
    with pytest.raises(ConfluenceToolError, match="não é do espaço"):
        await writer(wiki).draft_update(page_id, GLOSSARY, "Resumo da mudança", None)


@pytest.mark.req("F20-RT-08")
async def test_pagina_grande_demais_e_recusada() -> None:
    wiki = FakeWiki()
    wiki.add_space()
    huge = "\n\n".join(f"Parágrafo {i} " + "y" * 200 for i in range(MAX_STORAGE // 200))
    with pytest.raises(ConfluenceToolError, match="mil caracteres"):
        await writer(wiki).draft_create("arquitetura", "Arquitetura", huge, "Visão")


@pytest.mark.req("F20-RF-01")
async def test_espaco_proposto_com_as_9_paginas_do_modelo() -> None:
    wiki = FakeWiki()
    draft = await SpaceCreatorAdapter(wiki.client(), "LOJA").draft_space("Loja")

    assert draft.kind == "create_space"
    assert (draft.payload["space_key"], draft.payload["space_name"]) == (
        "LOJA",
        "Loja — Documentação",
    )
    titles = [p["title"] for p in draft.payload["pages"]]
    assert titles == draft.preview["pages"]
    assert titles[0] == "Início"
    assert len(titles) == 9
    home = draft.payload["pages"][0]
    assert "specflow-projeto-loja" in home["labels"]
    constitution = draft.payload["pages"][1]
    assert constitution["storage"].startswith("<h1>Constituição — Loja</h1>")
    assert wiki.writes == []


@pytest.mark.req("F20-RF-01")
async def test_chave_ocupada_pede_o_vinculo() -> None:
    wiki = FakeWiki()
    wiki.add_space("SCRUM", "Já existe")
    with pytest.raises(ConfluenceToolError, match="vinculá-lo em Projects"):
        await SpaceCreatorAdapter(wiki.client(), "SCRUM").draft_space("Scrum")
    assert space_key_for("AB_1") == "AB1"
