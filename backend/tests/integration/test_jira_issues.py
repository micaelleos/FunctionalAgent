"""Histórico de issues no Firestore do emulador (F10-RT-01..03): transação, ordem, cursor."""

from datetime import UTC, datetime, timedelta

import pytest
from google.cloud import firestore

from app.repositories.actions import ActionRepository

UID = "u-hist"


def _action(repo: ActionRepository, cid: str) -> str:
    return repo.create_action(UID, {"conversationId": cid, "status": "executing"})


@pytest.mark.req("F10-RT-01")
@pytest.mark.req("F10-RT-02")
@pytest.mark.req("F10-RT-03")
def test_registro_ordem_cursor_periodo_e_conversa_excluida(db: firestore.Client) -> None:
    repo = ActionRepository(db)
    t0 = datetime(2026, 11, 1, tzinfo=UTC)
    cid = repo.create_conversation(UID, {"title": "Pix", "createdAt": t0, "messageCount": 0})
    for i, key in enumerate(["ABC-1", "ABC-2", "ABC-3"]):
        aid = _action(repo, cid)
        at = t0 + timedelta(days=i)
        repo.complete_action(
            UID,
            aid,
            {"status": "done"},
            key,
            {"conversationId": cid, "createdAt": at, "operation": "created"},
            {},
        )
        assert (repo.get_action(UID, aid) or {})["status"] == "done"

    # Atualização: `first_time` não sobrescreve a 1ª gravação.
    aid = _action(repo, cid)
    later = t0 + timedelta(days=9)
    repo.complete_action(
        UID,
        aid,
        {"status": "done"},
        "ABC-1",
        {"updatedAt": later, "conversationId": cid},
        {"createdAt": later, "operation": "updated"},
    )
    first = repo.get_issue(UID, "ABC-1") or {}
    assert (first["createdAt"], first["operation"], first["updatedAt"]) == (t0, "created", later)

    page1 = repo.list_issues(UID, 2, None, None, None)
    assert [d["key"] for d in page1] == ["ABC-3", "ABC-2"]
    page2 = repo.list_issues(UID, 2, (page1[-1]["createdAt"], page1[-1]["key"]), None, None)
    assert [d["key"] for d in page2] == ["ABC-1"]
    ranged = repo.list_issues(UID, 10, None, t0 + timedelta(hours=1), t0 + timedelta(days=2))
    assert [d["key"] for d in ranged] == ["ABC-2"]
    assert repo.conversation_titles(UID, [cid, "sumiu"]) == {cid: "Pix"}

    repo.delete_conversation(UID, cid)

    assert [d["conversationId"] for d in repo.list_issues(UID, 10, None, None, None)] == [
        None,
        None,
        None,
    ]
