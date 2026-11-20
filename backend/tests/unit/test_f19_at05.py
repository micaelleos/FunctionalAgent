"""AT-F19-05 em processo: Confluence recusando (403) com o chat, o vínculo e o Jira reais.

Não há conta de sandbox sem Confluence; o Confluence é simulado e o modelo é roteirizado. O que se
verifica é o código: a story é proposta como hoje, o agente recebe a nota de "sem documentação" e
a conexão do Jira continua válida (F19-RF-09).
"""

from datetime import UTC, datetime
from typing import cast

import httpx
import pytest
from langchain_core.messages import AIMessage

from app.agent.fake_llm import ScriptedChatModel
from app.core.config import Settings
from app.integrations.confluence.client import ConfluenceClient
from app.services.chat import NO_DOCS_NOTE, ChatService
from app.services.confluence_links import ConfluenceLinkService
from app.services.conversations import ConversationService
from app.services.jira_connections import JiraConnectionService
from tests.chat_fakes import NOW, SITE, FakeJiraService, MemoryChatStore, call
from tests.fakes import MemoryLinkStore
from tests.spec_fixtures import pix_story_data


class JiraWithForbiddenConfluence(FakeJiraService):
    def __init__(self) -> None:
        super().__init__()
        self.confluence_requests: list[httpx.Request] = []

    async def confluence_client_for(self, uid: str, connection_id: str) -> ConfluenceClient:
        def forbidden(request: httpx.Request) -> httpx.Response:
            self.confluence_requests.append(request)
            return httpx.Response(403, json={"message": "Current user not permitted"})

        async def no_sleep(_: float) -> None:
            return None

        return ConfluenceClient(
            SITE, "po@teste.dev", "x" * 12, transport=httpx.MockTransport(forbidden), sleep=no_sleep
        )


@pytest.mark.req("F19-RF-09")
async def test_at_f19_05_sem_acesso_ao_confluence_a_story_sai_como_hoje() -> None:
    store, jira, links = MemoryChatStore(), JiraWithForbiddenConfluence(), MemoryLinkStore()
    links.set(
        "uid-alice",
        "ABC",
        {
            "connectionId": "conn-1",
            "spaceId": "65801",
            "spaceKey": "ABC",
            "spaceName": "Loja",
            "spaceUrl": f"{SITE}/wiki/spaces/ABC",
            "source": "same-key",
            "linkedAt": datetime(2026, 11, 20, tzinfo=UTC),
        },
    )
    connections = cast(JiraConnectionService, jira)
    llm = ScriptedChatModel(
        responses=[
            call("propor_criacao_issue", {"project_key": "ABC", "spec": pix_story_data()}),
            AIMessage("Sem a documentação do projeto. A proposta aguarda confirmação no cartão."),
        ]
    )
    service = ChatService(
        store,
        connections,
        llm,
        Settings(env="test", confluence_enabled=True),
        clock=lambda: NOW,
        confluence=ConfluenceLinkService(links, connections),
    )
    conv = await ConversationService(store, clock=lambda: NOW).create("uid-alice", None, "ABC")

    _, events = await service.open_turn("uid-alice", conv.id, "Crie a story do Pix")
    kinds = [str(getattr(e, "event")) for e in [e async for e in events]]  # noqa: B009

    assert "action_proposed" in kinds
    assert "error" not in kinds
    assert NO_DOCS_NOTE in str(llm.calls[0][0].content)
    assert "ler_pagina_confluence" not in llm.bound_tools
    assert jira.confluence_requests, "o índice do espaço foi pedido ao Confluence"
    assert jira.invalidated == []
