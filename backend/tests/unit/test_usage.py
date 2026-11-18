"""Cota diária e rate limit (F11-RF-01..03, F11-RT-05/06)."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.agent.fake_llm import ScriptedChatModel
from app.api.deps import get_chat_service, get_usage_service, get_verifier
from app.core.config import Settings, get_settings
from app.core.errors import ApiProblemError
from app.main import create_app
from app.services.chat import ChatService
from app.services.usage import UsageService, resets_at, usage_day
from tests.chat_fakes import FakeJiraService, MemoryChatStore
from tests.fakes import FakeVerifier

UID = "uid-alice"


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def _usage(store: MemoryChatStore, clock: Clock, **limits: Any) -> UsageService:
    return UsageService(store, Settings(env="test", **limits), clock=clock)


async def _code(coro: Any) -> ApiProblemError:
    with pytest.raises(ApiProblemError) as info:
        await coro
    return info.value


def test_dia_e_renovacao_no_horario_de_brasilia() -> None:
    # 01:30 UTC de 17/11 ainda é 22:30 de 16/11 em Brasília.
    late = datetime(2026, 11, 17, 1, 30, tzinfo=UTC)
    assert usage_day(late) == "2026-11-16"
    assert resets_at(late) == datetime(2026, 11, 17, 3, 0, tzinfo=UTC)


@pytest.mark.req("F11-RF-02")
@pytest.mark.req("F11-RT-05")
async def test_cota_de_mensagens_e_renovacao() -> None:
    store, clock = MemoryChatStore(), Clock(datetime(2026, 11, 17, 12, 0, tzinfo=UTC))
    usage = _usage(store, clock, daily_message_quota=3)

    for _ in range(3):
        await usage.reserve(UID)
        clock.now += timedelta(minutes=1)
    problem = await _code(usage.reserve(UID))

    assert (problem.status, problem.code) == (429, "quota-exceeded")
    assert problem.extra["resets_at"] == "2026-11-18T03:00:00+00:00"
    assert (
        problem.detail == "Você atingiu o limite diário. Ele renova às 00:00 (horário de Brasília)."
    )
    assert int(problem.headers["Retry-After"]) > 0
    clock.now = datetime(2026, 11, 18, 3, 0, tzinfo=UTC)  # meia-noite em Brasília
    await usage.reserve(UID)
    assert (await usage.usage(UID)).messages_today == 1


@pytest.mark.req("F11-RT-05")
async def test_cota_de_tokens() -> None:
    store, clock = MemoryChatStore(), Clock(datetime(2026, 11, 17, 12, 0, tzinfo=UTC))
    usage = _usage(store, clock, daily_token_quota=1000)
    await usage.reserve(UID)
    store.add_usage(UID, usage_day(clock.now), 900, 100)

    problem = await _code(usage.reserve(UID))

    assert problem.code == "quota-exceeded"


@pytest.mark.req("F11-RF-03")
@pytest.mark.req("F11-RT-06")
async def test_rate_limit_janela_de_60s_nao_gasta_cota() -> None:
    store, clock = MemoryChatStore(), Clock(datetime(2026, 11, 17, 12, 0, tzinfo=UTC))
    usage = _usage(store, clock, daily_message_quota=20)

    for _ in range(10):
        await usage.reserve(UID)
        clock.now += timedelta(seconds=0.5)
    problem = await _code(usage.reserve(UID))

    assert (problem.status, problem.code) == (429, "rate-limited")
    assert problem.headers["Retry-After"] == str(problem.extra["retry_after"])
    assert 1 <= problem.extra["retry_after"] <= 60
    assert (await usage.usage(UID)).messages_today == 10  # a recusada não contou
    clock.now += timedelta(seconds=problem.extra["retry_after"])
    await usage.reserve(UID)


@pytest.mark.req("F11-RT-06")
async def test_rate_limit_e_por_usuario() -> None:
    store, clock = MemoryChatStore(), Clock(datetime(2026, 11, 17, 12, 0, tzinfo=UTC))
    usage = _usage(store, clock, rate_limit_per_minute=2)
    await usage.reserve(UID)
    await usage.reserve(UID)

    await usage.reserve("uid-bob")
    assert (await _code(usage.reserve(UID))).code == "rate-limited"


@pytest.mark.req("F11-RF-01")
async def test_consumo_do_dia_e_7_dias() -> None:
    store, clock = MemoryChatStore(), Clock(datetime(2026, 11, 17, 12, 0, tzinfo=UTC))
    usage = _usage(store, clock)
    await usage.reserve(UID)
    clock.now += timedelta(days=1)
    await usage.reserve(UID)
    await usage.reserve(UID)
    store.add_usage(UID, usage_day(clock.now), 10, 5)

    out = await usage.usage(UID)

    assert (out.messages_today, out.message_limit) == (2, 20)
    assert (out.tokens_today, out.token_limit) == (15, 200_000)
    assert [d.messages for d in out.last_7_days] == [0, 0, 0, 0, 0, 1, 2]
    assert out.last_7_days[-1].day == "2026-11-18"


# --- rotas -----------------------------------------------------------------------------------


@pytest.mark.req("F11-RF-01")
@pytest.mark.req("F11-RF-02")
def test_rotas_429_antes_de_criar_conversa_e_consumo() -> None:
    store = MemoryChatStore()
    clock = Clock(datetime.now(UTC))
    settings = Settings(env="test", daily_message_quota=1)
    usage = UsageService(store, settings, clock=clock)
    chat = ChatService(
        store,
        FakeJiraService(),  # type: ignore[arg-type]
        ScriptedChatModel(responses=[AIMessage("Oi")]),
        settings,
        usage=usage,
    )
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_verifier] = FakeVerifier
    app.dependency_overrides[get_chat_service] = lambda: chat
    app.dependency_overrides[get_usage_service] = lambda: usage
    headers = {"Authorization": "Bearer ok:alice"}
    url = "/api/v1/conversations/new/messages"

    with TestClient(app) as client:
        first = client.post(url, json={"content": "Olá"}, headers=headers)
        second = client.post(url, json={"content": "De novo"}, headers=headers)
        me = client.get("/api/v1/me/usage", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["code"] == "quota-exceeded"
    assert "retry-after" in second.headers
    assert len(store.conversations[UID]) == 1  # a recusada não criou conversa
    body = me.json()
    assert (body["messages_today"], body["message_limit"]) == (1, 1)
    assert len(body["last_7_days"]) == 7
