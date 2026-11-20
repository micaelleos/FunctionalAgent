"""Registro das páginas escritas pelo SpecFlow no Firestore do emulador (F20-RT-07, F20-RF-08)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from google.cloud import firestore

from app.repositories.actions import ActionRepository
from app.repositories.documents import DocumentRepository
from tests.integration.conftest import AuthEmulator

T0 = datetime(2026, 11, 20, 12, tzinfo=UTC)


def _record(title: str, project: str, when: datetime, version: int = 1) -> dict[str, object]:
    return {
        "projectKey": project,
        "spaceId": "65801",
        "spaceKey": project,
        "type": "glossario",
        "title": title,
        "url": f"https://x.atlassian.net/wiki/{title}",
        "version": version,
        "operation": "created",
        "createdAt": when,
        "updatedAt": when,
    }


@pytest.mark.req("F20-RT-07")
@pytest.mark.req("F20-RF-08")
def test_conclusao_grava_documentos_na_mesma_transacao(
    client: TestClient, auth_emulator: AuthEmulator, db: firestore.Client
) -> None:
    alice = auth_emulator.create_user()
    actions = ActionRepository(db)
    action_id = actions.create_action(alice.uid, {"kind": "create_page", "status": "executing"})

    actions.complete_doc_action(
        alice.uid, action_id, {"status": "done"}, {"901": _record("Glossário", "SCRUM", T0)}
    )
    later = T0 + timedelta(hours=1)
    update = _record("Glossário", "SCRUM", later, 2) | {"operation": "updated"}
    actions.complete_doc_action(alice.uid, action_id, {"status": "done"}, {"901": update})
    actions.complete_doc_action(
        alice.uid, action_id, {"status": "done"}, {"902": _record("Roadmap", "OUTRO", T0)}
    )

    raw = (
        db.collection("users").document(alice.uid).collection("documents").document("901").get()
    ).to_dict() or {}
    assert raw["createdAt"] == T0  # a 1ª gravação não muda numa atualização
    assert (raw["version"], raw["operation"]) == (2, "updated")
    assert not {"storage", "content", "markdown"} & set(raw)  # só metadados
    assert actions.get_action(alice.uid, action_id)["status"] == "done"  # type: ignore[index]
    assert [d["pageId"] for d in DocumentRepository(db).list_documents(alice.uid)] == ["901", "902"]

    listed = client.get("/api/v1/documents?project=SCRUM", headers=alice.headers)
    assert listed.status_code == 200, listed.text
    [doc] = listed.json()
    assert (doc["page_id"], doc["title"], doc["version"]) == ("901", "Glossário", 2)
    bob = auth_emulator.create_user()
    assert client.get("/api/v1/documents", headers=bob.headers).json() == []
