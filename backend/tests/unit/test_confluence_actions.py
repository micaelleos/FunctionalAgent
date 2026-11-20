"""Confirmação das ações do Confluence (F20-RF-01, F20-RF-04, F20-RF-07, F20-RT-01, F20-RT-06)."""

import logging
from datetime import timedelta
from typing import Any, cast

import pytest

from app.agent.spec.jira_payload import payload_hash
from app.agent.tools.context import PageDraft
from app.core.config import Settings
from app.core.errors import ApiProblemError
from app.integrations.confluence.client import (
    ConfluenceConflictError,
    ConfluenceUncertainError,
)
from app.services.actions import ActionService, DocResult
from app.services.chat import ACTION_TTL
from app.services.confluence_actions import ConfluenceActionExecutor, append_row, translate
from app.services.confluence_writer import SpaceCreatorAdapter
from app.services.jira_connections import JiraConnectionService
from tests.chat_fakes import NOW, FakeJiraService, MemoryChatStore
from tests.confluence_fake import FakeWiki
from tests.fakes import MemoryLinkStore
from tests.jira_fake import SITE
from tests.unit.test_confluence_writer import GLOSSARY, writer

UID = "alice"
TERMS = "<h2>Termos</h2><p>Pedido</p>"
ON = Settings(env="test", confluence_enabled=True, confluence_write_enabled=True)


def setup(
    settings: Settings = ON,
) -> tuple[ActionService, MemoryChatStore, FakeWiki, MemoryLinkStore]:
    store, jira, wiki, links = MemoryChatStore(), FakeJiraService(), FakeWiki(), MemoryLinkStore()
    jira.wiki = wiki
    store.conversations[UID] = {"conv-1": {"messageCount": 2}}
    service = ActionService(
        store,
        cast(JiraConnectionService, jira),
        settings,
        clock=lambda: NOW,
        docs=ConfluenceActionExecutor(links, lambda: NOW),
    )
    return service, store, wiki, links


def propose(store: MemoryChatStore, draft: PageDraft, **extra: Any) -> str:
    doc = {
        "kind": draft.kind,
        "payload": draft.payload,
        "payloadHash": payload_hash(draft.payload),
        "readiness": {},
        "labels": [],
        "preview": draft.preview,
        "status": "pending",
        "conversationId": "conv-1",
        "connectionId": "conn-1",
        "siteUrl": SITE,
        "createdAt": NOW - timedelta(minutes=5),
        "expiresAt": NOW - timedelta(minutes=5) + ACTION_TTL,
    } | extra
    return store.create_action(UID, doc)


def with_registry(wiki: FakeWiki) -> str:
    wiki.add_space()
    return wiki.add_page(
        "Registro de mudanças",
        "<table><tbody><tr><th>Data</th><th>Página</th><th>Resumo</th><th>Autor</th></tr>"
        "</tbody></table>",
        ["specflow-tipo-registro"],
    )


@pytest.mark.req("F20-RT-01")
@pytest.mark.req("F20-RF-07")
@pytest.mark.req("F20-RT-06")
async def test_confirmar_cria_a_pagina_e_a_linha_do_registro(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service, store, wiki, _ = setup()
    registry = with_registry(wiki)
    draft = await writer(wiki).draft_create("glossario", "Glossário", GLOSSARY, "Termo Pedido")
    aid = propose(store, draft)
    assert wiki.writes == []

    with caplog.at_level(logging.INFO, logger="app.actions"):
        out = await service.confirm(UID, aid, "Ana")

    page = wiki.by_title("Glossário")
    assert page["storage"] == draft.payload["storage"]  # exatamente o que foi exibido
    assert page["labels"] == ["specflow", "specflow-tipo-glossario"]
    assert page["parentId"] == wiki.spaces["SCRUM"]["homepageId"]
    row = wiki.pages[registry]["storage"]
    assert "Termo Pedido" in row
    assert "SpecFlow, confirmado por Ana" in row
    assert f'/pages/{page["id"]}">Glossário</a>' in row
    assert out.status == "done"
    assert isinstance(out.result, DocResult)
    assert (out.result.page_id, out.result.warning) == (page["id"], None)
    record = store.list_documents(UID, "SCRUM")[0]
    assert (record["pageId"], record["type"], record["operation"]) == (
        page["id"],
        "glossario",
        "created",
    )
    assert any("criou a página" in m["content"] for m in store.messages[(UID, "conv-1")])
    [audit] = [r for r in caplog.records if r.getMessage() == "confluence_write"]
    fields = audit.__dict__["fields"]
    assert (fields["kind"], fields["result"], fields["page_id"]) == (
        "create_page",
        "done",
        page["id"],
    )
    assert isinstance(fields["duration_ms"], int)
    assert "Glossário" not in str(fields)  # sem título nem conteúdo


@pytest.mark.req("F20-RF-04")
async def test_pagina_editada_depois_da_proposta_nao_e_sobrescrita() -> None:
    service, store, wiki, _ = setup()
    with_registry(wiki)
    page_id = wiki.add_page(
        "Glossário", "<h2>Termos</h2><p>Pedido</p>", ["specflow-tipo-glossario"]
    )
    new = "# Glossário\n\n## Termos\nPedido confirmado\n"
    aid = propose(store, await writer(wiki).draft_update(page_id, new, "Pedido confirmado", None))
    wiki.pages[page_id].update(storage="<p>edição da Bia</p>", version=2)  # alguém editou

    with pytest.raises(ApiProblemError) as info:
        await service.confirm(UID, aid, "Ana")

    assert info.value.status == 422
    assert wiki.pages[page_id]["storage"] == "<p>edição da Bia</p>"
    action = store.get_action(UID, aid)
    assert action is not None
    assert (action["status"], action["error"]["code"]) == ("failed", "confluence-version-conflict")
    assert store.list_documents(UID) == []


@pytest.mark.req("F20-RF-03")
async def test_atualizacao_confirmada_sobe_a_versao() -> None:
    service, store, wiki, _ = setup()
    with_registry(wiki)
    page_id = wiki.add_page(
        "Glossário", "<h2>Termos</h2><p>Pedido</p>", ["specflow-tipo-glossario"]
    )
    new = "# Glossário\n\n## Termos\nPedido confirmado\n"
    aid = propose(store, await writer(wiki).draft_update(page_id, new, "Pedido confirmado", None))

    out = await service.confirm(UID, aid, None)

    assert wiki.pages[page_id]["version"] == 2
    assert "Pedido confirmado" in wiki.pages[page_id]["storage"]
    assert store.list_documents(UID)[0]["operation"] == "updated"
    assert isinstance(out.result, DocResult)


@pytest.mark.req("F20-RT-01")
async def test_payload_alterado_ou_flag_desligada_nao_escreve() -> None:
    service, store, wiki, _ = setup()
    with_registry(wiki)
    draft = await writer(wiki).draft_create("glossario", "Glossário", GLOSSARY, "Termo Pedido")
    tampered = propose(store, draft, payloadHash="outro")
    with pytest.raises(ApiProblemError):
        await service.confirm(UID, tampered)
    off, off_store, off_wiki, _ = setup(Settings(env="test", confluence_enabled=True))
    off_wiki.add_space()
    aid = propose(off_store, draft)
    with pytest.raises(ApiProblemError) as info:
        await off.confirm(UID, aid)

    assert info.value.status == 503
    assert [r.method for r in wiki.writes] == []
    assert off_wiki.writes == []
    pending = off_store.get_action(UID, aid)
    assert pending is not None
    assert pending["status"] == "pending"


@pytest.mark.req("F20-RT-01")
async def test_recusar_nao_escreve_nada() -> None:
    service, store, wiki, _ = setup()
    with_registry(wiki)
    aid = propose(
        store, await writer(wiki).draft_create("glossario", "Glossário", GLOSSARY, "x" * 5)
    )
    out = await service.reject(UID, aid)
    assert out.status == "rejected"
    assert wiki.writes == []


@pytest.mark.req("F20-RF-01")
async def test_criar_espaco_com_o_modelo_e_vincular() -> None:
    service, store, wiki, links = setup()
    aid = propose(store, await SpaceCreatorAdapter(wiki.client(), "LOJA").draft_space("Loja"))

    out = await service.confirm(UID, aid, "Ana")

    space = wiki.spaces["LOJA"]
    titles = {p["title"] for p in wiki.pages.values() if p["spaceKey"] == "LOJA"}
    assert titles == {
        "Início",
        "Constituição",
        "Glossário",
        "Regras de negócio",
        "Arquitetura",
        "Decisões (ADR)",
        "Roadmap",
        "Features",
        "Registro de mudanças",
    }
    assert wiki.pages[space["homepageId"]]["title"] == "Início"
    assert wiki.by_title("Constituição")["parentId"] == space["homepageId"]
    assert "specflow-projeto-loja" in wiki.pages[space["homepageId"]]["labels"]
    assert "confirmado por Ana" in wiki.by_title("Registro de mudanças")["storage"]
    link = links.get(UID, "LOJA")
    assert link is not None
    assert (link["spaceKey"], link["connectionId"]) == ("LOJA", "conn-1")
    assert len(store.list_documents(UID, "LOJA")) == 9
    assert isinstance(out.result, DocResult)
    assert out.result.title == "Loja — Documentação"


@pytest.mark.req("F20-RF-01")
async def test_falha_no_meio_deixa_o_que_foi_criado_e_diz_o_que_falta() -> None:
    service, store, wiki, links = setup()
    aid = propose(store, await SpaceCreatorAdapter(wiki.client(), "LOJA").draft_space("Loja"))
    wiki.fail_create_after = 3

    with pytest.raises(ApiProblemError):
        await service.confirm(UID, aid)

    action = store.get_action(UID, aid)
    assert action is not None
    assert action["error"]["code"] == "confluence-partial"
    assert "Faltam: " in action["error"]["message"]
    assert "Registro de mudanças" in action["error"]["message"]
    assert links.get(UID, "LOJA") is not None  # o espaço criado já fica vinculado
    assert not any(r.method == "DELETE" for r in wiki.writes)


@pytest.mark.req("F20-RF-04")
def test_traducao_dos_erros_e_registro_sem_tabela() -> None:
    assert translate("update_page", {}, ConfluenceConflictError("x")).code == (
        "confluence-version-conflict"
    )
    assert translate("create_space", {"space_key": "X"}, ConfluenceConflictError("x")).code == (
        "confluence-space-key-taken"
    )
    uncertain = translate("create_page", {}, ConfluenceUncertainError("x"))
    assert (uncertain.code, uncertain.retryable) == ("confluence-uncertain", False)
    assert append_row("<p>x</p>", ["a", "b", "c", "d"]).endswith(
        "<tr><td>a</td><td>b</td><td>c</td><td>d</td></tr></tbody></table>"
    )
