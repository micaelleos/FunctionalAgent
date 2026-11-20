"""Chat com a documentação do projeto (F19-RF-04, F19-RF-09, F19-RT-02, F19-RT-11)."""

from typing import Any, cast

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from app.agent.fake_llm import ScriptedChatModel
from app.agent.tools.confluence_write_tools import WRITE_NOTE
from app.agent.tools.context import ConfluenceReader, DocsWriter, SpaceCreator
from app.core.config import Settings
from app.services.chat import NO_DOCS_NOTE, SPACE_NOTE, ChatService
from app.services.conversations import ConversationService
from app.services.jira_connections import JiraConnectionService
from tests.chat_fakes import NOW, FakeJiraService, MemoryChatStore, call
from tests.confluence_fake import FakeConfluenceReader


class _Client:
    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class FakeLinks:
    def __init__(
        self, reader: FakeConfluenceReader | None, creator: SpaceCreator | None = None
    ) -> None:
        self.reader = reader
        self.creator = creator
        self.client = _Client()
        self.asked: list[tuple[str, str, str]] = []

    async def reader_for(
        self, uid: str, project_key: str, connection_id: str
    ) -> tuple[ConfluenceReader, _Client] | None:
        self.asked.append((uid, project_key, connection_id))
        return (self.reader, self.client) if self.reader else None

    def writer_for(self, reader: Any, client: Any, project_key: str) -> DocsWriter | None:
        return cast(DocsWriter, object())

    async def space_creator_for(
        self, uid: str, project_key: str, connection_id: str
    ) -> tuple[SpaceCreator, _Client] | None:
        return (self.creator, self.client) if self.creator else None


async def _run(
    llm: ScriptedChatModel,
    links: FakeLinks,
    *,
    enabled: bool = True,
    project: str | None = "SCRUM",
    write: bool = False,
) -> tuple[MemoryChatStore, FakeJiraService]:
    store, jira = MemoryChatStore(), FakeJiraService()
    service = ChatService(
        store,
        cast(JiraConnectionService, jira),
        llm,
        Settings(env="test", confluence_enabled=enabled, confluence_write_enabled=write),
        clock=lambda: NOW,
        confluence=links,
    )
    conv = await ConversationService(store, clock=lambda: NOW).create("uid-alice", None, project)
    _, events = await service.open_turn("uid-alice", conv.id, "Crie a story de aprovação")
    [e async for e in events]
    return store, jira


def _system(llm: ScriptedChatModel) -> str:
    return str(llm.calls[0][0].content)


@pytest.mark.req("F19-RF-04")
@pytest.mark.req("F19-RT-02")
async def test_indice_na_instrucao_e_pagina_lida_no_turno() -> None:
    llm = ScriptedChatModel(
        responses=[call("ler_pagina_confluence", {"page_id": "101"}), AIMessage("Li a RN-03.")]
    )
    links = FakeLinks(FakeConfluenceReader())
    await _run(llm, links)

    system = _system(llm)
    assert "## Documentação do projeto no Confluence" in system
    assert "Regras de negócio" in system
    assert '"id": "101"' in system
    assert "RN-03" not in system  # só o índice; o conteúdo vem pela ferramenta
    tool = next(m for m in llm.calls[1] if isinstance(m, ToolMessage))
    assert "RN-03" in str(tool.content)
    assert links.asked == [("uid-alice", "SCRUM", "conn-1")]
    assert links.client.closed


@pytest.mark.req("F19-RF-04")
async def test_sem_vinculo_o_turno_segue_sem_documentacao() -> None:
    llm = ScriptedChatModel(responses=[AIMessage("ok")])
    await _run(llm, FakeLinks(None))
    assert NO_DOCS_NOTE in _system(llm)


@pytest.mark.req("F19-RT-11")
@pytest.mark.parametrize(("enabled", "project"), [(False, "SCRUM"), (True, None)])
async def test_flag_desligada_ou_sem_projeto_nao_consulta(enabled: bool, project: Any) -> None:
    llm = ScriptedChatModel(responses=[AIMessage("ok")])
    links = FakeLinks(FakeConfluenceReader())
    await _run(llm, links, enabled=enabled, project=project)
    assert links.asked == []
    assert "Confluence" not in _system(llm).split("## Ferramentas")[0][-200:]
    assert "## Documentação do projeto" not in _system(llm)


@pytest.mark.req("F19-RF-09")
async def test_confluence_recusado_nao_afeta_o_jira() -> None:
    llm = ScriptedChatModel(responses=[AIMessage("Sigo sem a documentação.")])
    links = FakeLinks(FakeConfluenceReader(fail=True))
    _store, jira = await _run(llm, links)

    assert NO_DOCS_NOTE in _system(llm)
    assert jira.invalidated == []
    assert links.client.closed


@pytest.mark.req("F19-RF-04")
@pytest.mark.parametrize(("reader", "sees_docs"), [(True, True), (False, False)])
async def test_ferramentas_do_confluence_so_com_espaco_vinculado(
    reader: bool, sees_docs: bool
) -> None:
    llm = ScriptedChatModel(responses=[AIMessage("ok")])
    await _run(llm, FakeLinks(FakeConfluenceReader() if reader else None))
    assert ("ler_pagina_confluence" in llm.bound_tools) is sees_docs
    assert "propor_criacao_issue" in llm.bound_tools


class _Creator:
    project_key = "SCRUM"

    async def draft_space(self, project_name: str) -> Any:
        raise AssertionError("não chamado")


@pytest.mark.req("F20-RT-01")
@pytest.mark.req("F20-RF-01")
@pytest.mark.parametrize(
    ("write", "linked", "expected", "absent"),
    [
        (True, True, ["ler_pagina_confluence", "propor_criacao_pagina"], ["propor_criacao_espaco"]),
        (False, True, ["ler_pagina_confluence"], ["propor_criacao_pagina"]),
        (
            True,
            False,
            ["propor_criacao_espaco"],
            ["ler_pagina_confluence", "propor_criacao_pagina"],
        ),
        (False, False, [], ["propor_criacao_espaco", "propor_criacao_pagina"]),
    ],
)
async def test_ferramentas_de_escrita_so_com_a_flag(
    write: bool, linked: bool, expected: list[str], absent: list[str]
) -> None:
    llm = ScriptedChatModel(responses=[AIMessage("ok")])
    links = FakeLinks(FakeConfluenceReader() if linked else None, _Creator())
    await _run(llm, links, write=write)
    for name in expected:
        assert name in llm.bound_tools
    for name in absent:
        assert name not in llm.bound_tools
    if write and not linked:
        assert SPACE_NOTE in _system(llm)
        assert links.client.closed
    assert (WRITE_NOTE in _system(llm)) is (write and linked)
