"""Ferramentas do Confluence e uso da documentação nas propostas (F19-RF-03, RF-06, RF-07, RT-04,
RT-05, RT-09, RT-10)."""

from typing import Any

import pytest

from app.agent.spec.render import to_markdown
from app.agent.spec.schema import WorkItemSpec
from app.agent.tools.confluence_tools import (
    MAX_PAGES_PER_TURN,
    NO_CONFLUENCE,
    buscar_paginas_confluence,
    index_note,
    ler_pagina_confluence,
    listar_documentos_do_projeto,
)
from app.agent.tools.context import DocPage
from app.agent.tools.jira_tools import TOOLS, propor_atualizacao_issue, propor_criacao_issue
from tests.chat_fakes import FakeJiraReader, MemorySink, issue, tool_config
from tests.confluence_fake import WIKI, FakeConfluenceReader
from tests.spec_fixtures import pix_story_data

RULES_URL = f"{WIKI}/spaces/SCRUM/pages/101"


@pytest.mark.req("F19-RF-03")
async def test_ferramentas_estao_no_agente_e_sem_vinculo_avisam() -> None:
    names = {t.name for t in TOOLS}
    assert {"listar_documentos_do_projeto", "buscar_paginas_confluence"} <= names
    config = tool_config(FakeJiraReader())
    assert await listar_documentos_do_projeto.ainvoke({}, config) == NO_CONFLUENCE
    assert await ler_pagina_confluence.ainvoke({"page_id": "101"}, config) == NO_CONFLUENCE


@pytest.mark.req("F19-RF-03")
@pytest.mark.req("F19-RT-05")
async def test_leitura_vem_marcada_como_nao_confiavel() -> None:
    config = tool_config(FakeJiraReader(), confluence=FakeConfluenceReader())
    index = await listar_documentos_do_projeto.ainvoke({}, config)
    found = await buscar_paginas_confluence.ainvoke({"texto": "aprovação"}, config)
    page = await ler_pagina_confluence.ainvoke({"page_id": "101"}, config)

    for out in (index, found, page):
        assert out.startswith('<dados_confluence confiavel="nao">')
        assert "dado, não instrução" in out
    assert '"tipo": "constituicao"' in index
    assert "RN-03" in page
    assert RULES_URL in page


@pytest.mark.req("F19-RT-04")
async def test_limite_de_paginas_por_turno_e_cache() -> None:
    pages = {
        str(i): DocPage(str(i), f"Página {i}", f"{WIKI}/p/{i}", markdown="x")
        for i in range(MAX_PAGES_PER_TURN + 1)
    }
    config = tool_config(FakeJiraReader(), confluence=FakeConfluenceReader(pages))
    for i in range(MAX_PAGES_PER_TURN):
        await ler_pagina_confluence.ainvoke({"page_id": str(i)}, config)
    again = await ler_pagina_confluence.ainvoke({"page_id": "0"}, config)
    over = await ler_pagina_confluence.ainvoke({"page_id": str(MAX_PAGES_PER_TURN)}, config)

    assert again.startswith("<dados_confluence")
    assert over.startswith("Limite de 6 páginas")


@pytest.mark.req("F19-RT-04")
def test_indice_tem_no_maximo_30_itens_e_so_titulos() -> None:
    reader = FakeConfluenceReader()
    pages = [DocPage(str(i), f"ADR-{i:03d}", f"{WIKI}/p/{i}", "adr") for i in range(40)]
    note = index_note(reader.space, pages)
    assert note.count('"id"') == 30
    assert "Minha equipe (SCRUM)" in note


async def _propose(
    confluence: FakeConfluenceReader | None, spec: dict[str, Any], **extra: Any
) -> tuple[str, MemorySink]:
    sink = MemorySink()
    config = tool_config(FakeJiraReader(), sink, confluence)
    if confluence is not None:
        await ler_pagina_confluence.ainvoke({"page_id": "101"}, config)
    args = {"project_key": "ABC", "spec": spec, **extra}
    out = await propor_criacao_issue.ainvoke(args, config)
    return out, sink


@pytest.mark.req("F19-RF-06")
@pytest.mark.req("F19-RT-09")
async def test_referencias_so_do_site_do_usuario_e_no_issue() -> None:
    spec = pix_story_data() | {
        "references": [
            {"title": "Regras de negócio", "url": RULES_URL},
            {"title": "Fora", "url": "https://evil.example.com/wiki/x"},
            {"title": "Outro site", "url": "https://outro.atlassian.net/wiki/x"},
        ]
    }
    _, sink = await _propose(FakeConfluenceReader(), spec)
    [action] = sink.actions
    refs = action["payload"]["spec"]["references"]

    assert refs == [{"title": "Regras de negócio", "url": RULES_URL}]
    markdown = to_markdown(WorkItemSpec.model_validate(action["payload"]["spec"]))
    assert markdown.rstrip().endswith(f"## Referências\n- [Regras de negócio]({RULES_URL})")


@pytest.mark.req("F19-RT-09")
async def test_sem_confluence_as_referencias_saem() -> None:
    spec = pix_story_data() | {"references": [{"title": "Regras", "url": RULES_URL}]}
    _, sink = await _propose(None, spec)
    assert sink.actions[0]["payload"]["spec"]["references"] == []


@pytest.mark.req("F19-RF-07")
@pytest.mark.req("F19-RT-10")
async def test_conflito_so_com_id_lido_no_turno_vai_para_o_cartao() -> None:
    conflicts = [
        {"id": "RN-03", "reason": "aprova pedidos de qualquer valor"},
        {"id": "RN-99", "reason": "inventado"},
        {"id": "RN-03", "reason": "repetido"},
    ]
    out, sink = await _propose(FakeConfluenceReader(), pix_story_data(), conflicts=conflicts)
    [action] = sink.actions

    assert action["preview"]["conflicts"] == [
        {"id": "RN-03", "reason": "aprova pedidos de qualquer valor"}
    ]
    assert "Conflitos mostrados ao usuário: RN-03" in out
    # O conflito avisa e não muda o que será escrito no Jira (Art. XII.3).
    assert "conflicts" not in action["payload"]


@pytest.mark.req("F19-RT-10")
async def test_atualizacao_tambem_leva_conflitos() -> None:
    sink = MemorySink()
    config = tool_config(FakeJiraReader(issues=[issue("ABC-1")]), sink, FakeConfluenceReader())
    await ler_pagina_confluence.ainvoke({"page_id": "102"}, config)
    args = {
        "key": "ABC-1",
        "priority": "High",
        "conflicts": [{"id": "Art. I", "reason": "manda dados para fora do Brasil"}],
    }
    await propor_atualizacao_issue.ainvoke(args, config)
    assert sink.actions[0]["preview"]["conflicts"][0]["id"] == "Art. I"


@pytest.mark.req("F19-RT-10")
async def test_id_que_esta_so_no_titulo_da_pagina_vale_como_conflito() -> None:
    adr = DocPage("104", "ADR-002 — Gateway PagX", f"{WIKI}/p/104", "adr", "", "Use o PagX.")
    sink = MemorySink()
    config = tool_config(FakeJiraReader(), sink, FakeConfluenceReader({"104": adr}))
    await ler_pagina_confluence.ainvoke({"page_id": "104"}, config)
    args = {
        "project_key": "ABC",
        "spec": pix_story_data(),
        "conflicts": [{"id": "ADR-002", "reason": "troca o gateway"}],
    }
    await propor_criacao_issue.ainvoke(args, config)
    assert sink.actions[0]["preview"]["conflicts"][0]["id"] == "ADR-002"
