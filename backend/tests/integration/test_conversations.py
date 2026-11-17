"""Conversas com o Firestore e o Auth dos emuladores (F07-RT-01..04; T001)."""

import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from google.cloud import firestore

from app.repositories.actions import ActionRepository
from app.services.conversations import ConversationService
from tests.integration.conftest import AuthEmulator

T0 = datetime(2026, 11, 17, 9, 0, tzinfo=UTC)
BASE = "/api/v1/conversations"


def _seed(db: firestore.Client, uid: str, count: int) -> None:
    """`count` conversas com `updatedAt` distintos, em lotes."""
    conversations = db.collection("users").document(uid).collection("conversations")
    for start in range(0, count, 400):
        batch = db.batch()
        for i in range(start, min(start + 400, count)):
            at = T0 + timedelta(minutes=i)
            batch.set(
                conversations.document(f"c{i:04d}"),
                {"title": f"Conversa {i}", "createdAt": at, "updatedAt": at, "messageCount": 0},
            )
        batch.commit()


@pytest.mark.req("F07-RF-02")
@pytest.mark.req("F07-RT-01")
def test_paginacao_real_percorre_tudo_sem_repetir(
    client: TestClient, auth_emulator: AuthEmulator, db: firestore.Client
) -> None:
    user = auth_emulator.create_user()
    _seed(db, user.uid, 45)

    seen: list[str] = []
    cursor: str | None = None
    while True:
        query = f"?limit=20&cursor={cursor}" if cursor else "?limit=20"
        page = client.get(BASE + query, headers=user.headers).json()
        seen += [c["id"] for c in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break

    assert seen == [f"c{i:04d}" for i in reversed(range(45))]


@pytest.mark.req("F07-RT-02")
def test_listagem_p95_abaixo_de_300ms_com_500_conversas(db: firestore.Client) -> None:
    uid = "uid-desempenho"
    _seed(db, uid, 500)
    repo = ActionRepository(db)
    repo.list_conversations(uid, 21, None)  # aquece o canal gRPC

    durations = []
    for _ in range(20):
        started = time.perf_counter()
        repo.list_conversations(uid, 21, None)
        durations.append(time.perf_counter() - started)

    p95 = sorted(durations)[int(len(durations) * 0.95) - 1]
    assert p95 < 0.3, durations


@pytest.mark.req("F07-RF-05")
@pytest.mark.req("F07-RT-03")
async def test_exclusao_recursiva_em_lotes_e_idempotente(db: firestore.Client) -> None:
    uid = "uid-exclusao"
    repo = ActionRepository(db)
    service = ConversationService(repo, clock=lambda: T0)
    created = await service.create(uid, "Checkout", None)
    other = await service.create(uid, "Outra", None)
    messages = db.collection("users").document(uid).collection("conversations")
    for start in range(0, 450, 400):  # mais que um lote de exclusão (DELETE_BATCH)
        batch = db.batch()
        for seq in range(start + 1, min(start + 400, 450) + 1):
            ref = messages.document(created.id).collection("messages").document()
            batch.set(ref, {"role": "user", "content": "x", "seq": seq, "createdAt": T0})
        batch.commit()
    base = {"kind": "create_issue", "status": "pending", "createdAt": T0, "expiresAt": T0}
    repo.create_action(uid, {**base, "conversationId": created.id})
    kept = repo.create_action(uid, {**base, "conversationId": other.id})

    await service.delete(uid, created.id)
    await service.delete(uid, created.id)

    assert repo.get_conversation(uid, created.id) is None
    assert list(messages.document(created.id).collection("messages").limit(1).stream()) == []
    remaining = db.collection("users").document(uid).collection("pending_actions").stream()
    assert [d.id for d in remaining] == [kept]
    assert repo.get_conversation(uid, other.id) is not None


@pytest.mark.req("F07-RT-04")
def test_mensagem_atualiza_contagem_e_atividade_no_mesmo_lote(db: firestore.Client) -> None:
    uid = "uid-lote"
    repo = ActionRepository(db)
    cid = repo.create_conversation(uid, {"title": "a", "createdAt": T0, "updatedAt": T0})
    later = T0 + timedelta(hours=1)

    repo.add_message(uid, cid, {"role": "user", "content": "oi", "seq": 1, "createdAt": later})
    repo.add_system_message(uid, cid, {"content": "aviso", "createdAt": later})

    doc = repo.get_conversation(uid, cid)
    assert doc is not None
    assert (doc["messageCount"], doc["updatedAt"]) == (2, later)
    assert repo.add_system_message(uid, "nao-existe", {"content": "x", "createdAt": later})
    assert repo.get_conversation(uid, "nao-existe") is None  # não recria a conversa excluída


@pytest.mark.req("F07-RF-04")
def test_titulo_automatico_respeita_o_renomeado(db: firestore.Client) -> None:
    uid = "uid-titulo"
    repo = ActionRepository(db)
    auto = repo.create_conversation(uid, {"title": "p", "titleSource": "auto", "createdAt": T0})
    named = repo.create_conversation(uid, {"title": "Meu", "titleSource": "user", "createdAt": T0})

    assert repo.set_title_if_auto(uid, auto, "Gerado") is True
    assert repo.set_title_if_auto(uid, named, "Gerado") is False
    assert repo.set_title_if_auto(uid, "nao-existe", "Gerado") is False

    assert [repo.get_conversation(uid, c)["title"] for c in (auto, named)] == ["Gerado", "Meu"]  # type: ignore[index]


@pytest.mark.req("F07-RF-03")
def test_historico_por_seq_decrescente(db: firestore.Client) -> None:
    uid = "uid-historico"
    repo = ActionRepository(db)
    cid = repo.create_conversation(uid, {"title": "a", "createdAt": T0})
    for seq in range(1, 8):
        repo.add_message(
            uid, cid, {"role": "user", "content": str(seq), "seq": seq, "createdAt": T0}
        )

    first = repo.list_messages_before(uid, cid, None, 3)
    older = repo.list_messages_before(uid, cid, first[-1]["seq"], 3)

    assert [d["seq"] for d in first + older] == [7, 6, 5, 4, 3, 2]
