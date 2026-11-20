"""Ferramentas de escrita do agente (F20-RF-01..03, F20-RT-01, F20-RT-08): só propõem."""

from typing import Any

import pytest

from app.agent.tools.confluence_tools import ler_pagina_confluence
from app.agent.tools.confluence_write_tools import (
    MAX_PAGE_PROPOSALS,
    NO_WRITER,
    ler_modelo_de_pagina,
    propor_atualizacao_pagina,
    propor_criacao_espaco,
    propor_criacao_pagina,
)
from app.agent.tools.context import REVIEW_PREFIX, ConfluenceToolError, PageDraft, tool_context
from tests.chat_fakes import MemorySink, tool_config
from tests.confluence_fake import FakeConfluenceReader

CONTENT = "# Glossário — Minha equipe\n\n| Termo | Definição |\n|---|---|\n| Pedido | compra |\n"


class FakeWriter:
    def __init__(self, fail: str | None = None) -> None:
        self.space = FakeConfluenceReader().space
        self.fail = fail
        self.calls: list[tuple[str, ...]] = []

    async def draft_create(self, kind: str, title: str, markdown: str, summary: str) -> PageDraft:
        self.calls.append(("create", kind, title))
        if self.fail:
            raise ConfluenceToolError(self.fail)
        return PageDraft("create_page", {"title": title, "storage": "<p/>"}, {"title": title})

    async def draft_update(
        self, page_id: str, markdown: str, summary: str, title: str | None
    ) -> PageDraft:
        self.calls.append(("update", page_id))
        return PageDraft("update_page", {"page_id": page_id}, {"title": "Regras de negócio"})


class FakeCreator:
    project_key = "SCRUM"

    async def draft_space(self, project_name: str) -> PageDraft:
        return PageDraft("create_space", {"space_key": "SCRUM"}, {"title": f"{project_name} — Doc"})


def config(writer: Any = None, creator: Any = None, sink: MemorySink | None = None) -> Any:
    cfg = tool_config(None, sink, confluence=FakeConfluenceReader())
    ctx = tool_context(cfg)
    ctx.docs_writer, ctx.space_creator = writer, creator
    return cfg


def create_args(title: str = "Glossário") -> dict[str, str]:
    return {"tipo": "glossario", "titulo": title, "conteudo": CONTENT, "resumo": "Termo Pedido"}


@pytest.mark.req("F20-RF-02")
@pytest.mark.req("F20-RT-01")
async def test_propor_pagina_so_cria_a_acao_proposta() -> None:
    sink, writer = MemorySink(), FakeWriter()
    reply = await propor_criacao_pagina.ainvoke(create_args(), config(writer, sink=sink))

    assert "Ação proposta act-1" in reply
    assert "Não diga que a página foi escrita" in reply
    [action] = sink.actions
    assert (action["kind"], action["preview"]["title"]) == ("create_page", "Glossário")
    assert writer.calls == [("create", "glossario", "Glossário")]


@pytest.mark.req("F20-RT-01")
async def test_sem_escrita_ligada_as_ferramentas_nao_propoem() -> None:
    sink = MemorySink()
    cfg = config(sink=sink)
    assert await propor_criacao_pagina.ainvoke(create_args(), cfg) == NO_WRITER
    assert await ler_modelo_de_pagina.ainvoke({"tipo": "adr"}, cfg) == NO_WRITER
    assert "não está disponível" in await propor_criacao_espaco.ainvoke(
        {"nome_do_projeto": "Scrum"}, cfg
    )
    assert sink.actions == []


@pytest.mark.req("F20-RF-03")
async def test_atualizar_exige_ler_a_pagina_no_turno() -> None:
    sink, writer = MemorySink(), FakeWriter()
    cfg = config(writer, sink=sink)
    args = {"page_id": "101", "conteudo": CONTENT, "resumo": "Regra RN-04"}

    first = await propor_atualizacao_pagina.ainvoke(args, cfg)
    await ler_pagina_confluence.ainvoke({"page_id": "101"}, cfg)
    second = await propor_atualizacao_pagina.ainvoke(args, cfg)

    assert first.startswith(REVIEW_PREFIX)
    assert "ler_pagina_confluence" in first
    assert "Ação proposta" in second
    assert writer.calls == [("update", "101")]


@pytest.mark.req("F20-RT-08")
async def test_limite_de_propostas_por_turno_e_erro_do_writer_volta_ao_modelo() -> None:
    sink = MemorySink()
    cfg = config(FakeWriter(), sink=sink)
    for i in range(MAX_PAGE_PROPOSALS):
        await propor_criacao_pagina.ainvoke(create_args(f"ADR-00{i} — x"), cfg)
    over = await propor_criacao_pagina.ainvoke(create_args("ADR-009 — y"), cfg)
    failing = await propor_criacao_pagina.ainvoke(
        create_args(), config(FakeWriter("já existe a página"))
    )

    assert len(sink.actions) == MAX_PAGE_PROPOSALS
    assert over.startswith(REVIEW_PREFIX)
    assert f"limite de {MAX_PAGE_PROPOSALS}" in over
    assert failing == f"{REVIEW_PREFIX}: já existe a página"


@pytest.mark.req("F20-RF-01")
async def test_espaco_uma_vez_por_turno() -> None:
    sink = MemorySink()
    cfg = config(creator=FakeCreator(), sink=sink)
    first = await propor_criacao_espaco.ainvoke({"nome_do_projeto": "Scrum"}, cfg)
    again = await propor_criacao_espaco.ainvoke({"nome_do_projeto": "Scrum"}, cfg)
    assert "criar o espaço" in first
    assert again.startswith(REVIEW_PREFIX)
    assert [a["kind"] for a in sink.actions] == ["create_space"]


@pytest.mark.req("F20-RT-05")
async def test_modelo_da_pagina_vem_preenchido_com_o_projeto() -> None:
    model = await ler_modelo_de_pagina.ainvoke({"tipo": "constituicao"}, config(FakeWriter()))
    assert model.startswith("# Constituição — Minha equipe")
    assert "**Projeto Jira:** SCRUM" in model


@pytest.mark.req("F20-RF-05")
@pytest.mark.req("F20-RF-06")
def test_instrucoes_de_convergir_e_adr_so_com_a_escrita() -> None:
    from app.agent.graph import system_prompt
    from app.agent.tools.confluence_write_tools import WRITE_NOTE

    for text in (
        "Roadmap",
        "chave do épico",
        "FEAT-nn",
        "ADR nova",
        "Proposta",
        "nunca é reutilizado",
    ):
        assert text in WRITE_NOTE
    v2 = " ".join(
        system_prompt(
            "v2", today=__import__("datetime").date(2026, 11, 20), jira_connected=True
        ).split()
    )
    assert '"Escrita da documentação"' in v2
    assert "você não escreve no Confluence" in v2
