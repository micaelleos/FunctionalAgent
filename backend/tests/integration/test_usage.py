"""Cota e rate limit na transação real do Firestore (F11-RT-05, F11-RT-06)."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from google.cloud import firestore

from app.core.config import Settings
from app.core.errors import ApiProblemError
from app.repositories.usage import UsageRepository
from app.services.usage import UsageService


@pytest.mark.req("F11-RT-05")
async def test_reservas_em_paralelo_nunca_passam_da_cota(db: firestore.Client) -> None:
    now = datetime.now(UTC)
    usage = UsageService(
        UsageRepository(db),
        Settings(env="test", daily_message_quota=5, rate_limit_per_minute=100),
        clock=lambda: now,
    )

    results = await asyncio.gather(
        *(usage.reserve("u-cota") for _ in range(10)), return_exceptions=True
    )

    accepted = [r for r in results if r is None]
    refused = [r for r in results if r is not None]
    assert all(isinstance(r, ApiProblemError) and r.status == 429 for r in refused), results
    assert 1 <= len(accepted) <= 5
    assert (await usage.usage("u-cota")).messages_today == len(accepted)
    # Sem colisão, a cota fecha exatamente em 5.
    later = await asyncio.gather(*(_sequential(usage) for _ in range(1)), return_exceptions=False)
    assert set(later[0]) <= {"ok", "quota-exceeded"}
    assert (await usage.usage("u-cota")).messages_today == 5


@pytest.mark.req("F11-RT-06")
async def test_janela_do_rate_limit_persistida(db: firestore.Client) -> None:
    clock = [datetime.now(UTC)]
    usage = UsageService(
        UsageRepository(db),
        Settings(env="test", rate_limit_per_minute=2),
        clock=lambda: clock[0],
    )
    await usage.reserve("u-rate")
    await usage.reserve("u-rate")

    with pytest.raises(ApiProblemError) as info:
        await usage.reserve("u-rate")
    assert info.value.code == "rate-limited"
    clock[0] += timedelta(seconds=61)
    await usage.reserve("u-rate")


async def _sequential(usage: UsageService) -> list[str]:
    codes = []
    for _ in range(10):
        try:
            await usage.reserve("u-cota")
            codes.append("ok")
        except ApiProblemError as exc:
            codes.append(exc.code)
    return codes
