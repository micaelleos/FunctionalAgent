"""Serviço de conversas (F07) sobre o store em memória: cursor, histórico, exclusão."""

from datetime import timedelta
from typing import Any

import pytest

from app.core.errors import ApiProblemError
from app.services.actions import ActionResult
from app.services.conversations import ConversationService, display_text
from tests.chat_fakes import NOW, MemoryChatStore

UID = "uid-alice"


def _service() -> tuple[ConversationService, MemoryChatStore]:
    store = MemoryChatStore()
    return ConversationService(store, clock=lambda: NOW), store


def _conversation(store: MemoryChatStore, title: str, minutes: int, uid: str = UID) -> str:
    at = NOW + timedelta(minutes=minutes)
    data = {"title": title, "createdAt": at, "updatedAt": at, "messageCount": 0}
    return store.create_conversation(uid, data)


def _message(store: MemoryChatStore, cid: str, role: str, seq: int, **extra: Any) -> str:
    data = {"role": role, "content": f"{role} {seq}", "seq": seq, "createdAt": NOW, **extra}
    return store.add_message(UID, cid, data)


async def _problem(coro: Any) -> ApiProblemError:
    with pytest.raises(ApiProblemError) as info:
        await coro
    return info.value


@pytest.mark.req("F07-RF-02")
@pytest.mark.req("F07-RT-01")
async def test_lista_por_ultima_atividade_com_cursor() -> None:
    service, store = _service()
    for i, title in enumerate(["a", "b", "c", "d", "e"]):
        _conversation(store, title, minutes=i)
    _conversation(store, "de outro", minutes=99, uid="uid-bob")

    first = await service.list(UID, None, 2)
    second = await service.list(UID, first.next_cursor, 2)
    last = await service.list(UID, second.next_cursor, 2)

    assert [c.title for c in first.items + second.items + last.items] == ["e", "d", "c", "b", "a"]
    assert last.next_cursor is None


@pytest.mark.req("F07-RT-01")
@pytest.mark.parametrize("cursor", ["@@", "bm90LWpzb24", "WzFd", "eyJzIjogMH0"])
async def test_cursor_invalido_e_400(cursor: str) -> None:
    service, store = _service()
    cid = _conversation(store, "a", 0)

    for coro in (service.list(UID, cursor, 10), service.messages(UID, cid, cursor, 10)):
        problem = await _problem(coro)
        assert (problem.status, problem.code) == (400, "invalid-cursor")


@pytest.mark.req("F07-RF-01")
async def test_criar_com_projeto_e_titulo_padrao() -> None:
    service, store = _service()

    created = await service.create(UID, None, "SCRUM")

    assert (created.title, created.project_key, created.message_count) == (
        "Nova conversa",
        "SCRUM",
        0,
    )
    assert store.conversations[UID][created.id]["titleSource"] == "auto"
    named = await service.create(UID, "Checkout", None)
    assert store.conversations[UID][named.id]["titleSource"] == "user"


@pytest.mark.req("F07-RF-04")
@pytest.mark.req("F07-RF-06")
async def test_renomear_e_fixar_ou_soltar_projeto() -> None:
    service, store = _service()
    cid = _conversation(store, "a", 0)

    renamed = await service.update(UID, cid, {"title": "Checkout v2"})
    pinned = await service.update(UID, cid, {"project_key": "SCRUM"})
    loose = await service.update(UID, cid, {"project_key": None})

    assert (renamed.title, pinned.project_key, loose.project_key) == ("Checkout v2", "SCRUM", None)
    assert store.conversations[UID][cid]["titleSource"] == "user"
    assert loose.title == "Checkout v2"


@pytest.mark.req("F07-RF-03")
async def test_conversa_de_outro_usuario_e_404() -> None:
    service, store = _service()
    cid = _conversation(store, "do bob", 0, uid="uid-bob")

    for coro in (
        service.get(UID, cid),
        service.update(UID, cid, {"title": "x"}),
        service.messages(UID, cid, None, 10),
    ):
        problem = await _problem(coro)
        assert (problem.status, problem.code) == (404, "conversation-not-found")
    assert store.conversations["uid-bob"][cid]["title"] == "do bob"


@pytest.mark.req("F07-RF-03")
async def test_historico_paginado_so_usuario_e_agente_com_acoes() -> None:
    service, store = _service()
    cid = _conversation(store, "a", 0)
    action = {
        "conversationId": cid,
        "kind": "create_issue",
        "status": "done",
        "preview": {"summary": "Pix"},
        "readiness": {"ready": True, "rules": []},
        "labels": ["specflow"],
        "createdAt": NOW,
        "expiresAt": NOW + timedelta(hours=24),
        "result": {"issue_key": "ABC-1", "url": "https://x/browse/ABC-1"},
    }
    aid = store.create_action(UID, action)
    seq = 0
    for turn in range(3):
        _message(store, cid, "user", seq := seq + 1)
        _message(store, cid, "tool", seq := seq + 1)
        extra = {"actions": [{"id": aid, "kind": "create_issue"}]} if turn == 1 else {}
        _message(store, cid, "assistant", seq := seq + 1, **extra)
    _message(store, cid, "system", seq := seq + 1)

    recent = await service.messages(UID, cid, None, 4)
    older = await service.messages(UID, cid, recent.next_cursor, 4)

    assert [m.text for m in older.items + recent.items] == [
        "user 1",
        "assistant 3",
        "user 4",
        "assistant 6",
        "user 7",
        "assistant 9",
    ]
    assert older.next_cursor is None
    [card] = recent.items[1].actions  # "assistant 6", do 2º turno
    assert (card.id, card.status) == (aid, "done")
    assert card.result == ActionResult(issue_key="ABC-1", url="https://x/browse/ABC-1")
    assert [m.actions for m in recent.items if m is not recent.items[1]] == [[], [], []]


@pytest.mark.req("F07-RF-03")
async def test_historico_atravessa_muitas_mensagens_de_ferramenta() -> None:
    service, store = _service()
    cid = _conversation(store, "a", 0)
    _message(store, cid, "user", 1)
    for seq in range(2, 252):
        _message(store, cid, "tool", seq)
    _message(store, cid, "assistant", 252)

    page = await service.messages(UID, cid, None, 50)

    assert [m.role for m in page.items] == ["user", "assistant"]
    assert page.next_cursor is None


@pytest.mark.req("F07-RF-03")
def test_texto_visivel_sem_notas_para_o_modelo() -> None:
    legacy = {
        "content": "Pronto.\n[Ação proposta act-1: create_issue Pix — aguardando confirmação]"
    }

    assert display_text(legacy) == "Pronto."
    assert display_text({"content": "x\n[Ação proposta a]", "text": "x"}) == "x"
    assert (
        display_text({"content": "Veja [Ação proposta] no texto"})
        == "Veja [Ação proposta] no texto"
    )


@pytest.mark.req("F07-RF-05")
@pytest.mark.req("F07-RT-03")
async def test_excluir_apaga_mensagens_e_acoes_e_e_idempotente() -> None:
    service, store = _service()
    cid = _conversation(store, "a", 0)
    other = _conversation(store, "b", 1)
    _message(store, cid, "user", 1)
    base = {"kind": "create_issue", "createdAt": NOW, "expiresAt": NOW}
    store.create_action(UID, {**base, "conversationId": cid, "status": "pending"})
    keep = store.create_action(UID, {**base, "conversationId": other, "status": "pending"})
    store.save_issue(UID, "ABC-1", {"conversationId": cid})

    await service.delete(UID, cid)
    await service.delete(UID, cid)

    assert cid not in store.conversations[UID]
    assert (UID, cid) not in store.messages
    assert [a["id"] for a in store.actions[UID]] == [keep]
    assert "ABC-1" in store.issues[UID]  # a issue existe no Jira; o histórico (F10) mantém


@pytest.mark.req("F07-RT-03")
async def test_acao_em_execucao_impede_a_exclusao() -> None:
    service, store = _service()
    cid = _conversation(store, "a", 0)
    store.create_action(
        UID,
        {"conversationId": cid, "kind": "create_issue", "status": "executing", "createdAt": NOW},
    )

    problem = await _problem(service.delete(UID, cid))

    assert (problem.status, problem.code) == (409, "conversation-busy")
    assert cid in store.conversations[UID]


@pytest.mark.req("F08-RT-09")
async def test_historico_marca_a_resposta_interrompida() -> None:
    service, store = _service()
    cid = _conversation(store, "a", 0)
    _message(store, cid, "user", 1)
    _message(store, cid, "assistant", 2, text="Parcial", interrupted=True)

    [user, assistant] = (await service.messages(UID, cid, None, 10)).items

    assert (user.interrupted, assistant.interrupted, assistant.text) == (False, True, "Parcial")
