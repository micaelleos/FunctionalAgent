"""Cota diária e rate limit por usuário (F11-RF-01..03, F11-RT-05/06).

`reserve` roda antes de o turno chamar o modelo: confere a janela de 60 s e a cota do dia de
Brasília e já conta a mensagem. Os tokens do turno entram depois, em `add_usage` (F05).
"""

import logging
import math
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta, timezone
from typing import Any, Protocol

from pydantic import BaseModel

from app.core.errors import ApiProblemError
from app.core.logging import uid_hash
from app.core.telemetry import in_thread
from app.repositories.usage import UsageConflictError

# Brasília não tem horário de verão desde 2019: UTC-3 fixo (sem depender do tzdata da imagem).
BRASILIA = timezone(timedelta(hours=-3), "America/Sao_Paulo")
WINDOW = timedelta(seconds=60)
log = logging.getLogger("app.usage")
HISTORY_DAYS = 7


def usage_day(now: datetime) -> str:
    return now.astimezone(BRASILIA).date().isoformat()


def resets_at(now: datetime) -> datetime:
    tomorrow = now.astimezone(BRASILIA).date() + timedelta(days=1)
    return datetime.combine(tomorrow, time(0, 0), BRASILIA).astimezone(UTC)


class UsageStore(Protocol):
    def update_usage(
        self,
        uid: str,
        day: str,
        decide: Callable[[dict[str, Any]], tuple[dict[str, Any] | None, Any]],
    ) -> Any: ...
    def usage_days(self, uid: str, days: list[str]) -> dict[str, dict[str, Any]]: ...


class UsageLimits(Protocol):
    daily_message_quota: int
    daily_token_quota: int
    rate_limit_per_minute: int


class QuotaExceededError(ApiProblemError):
    def __init__(self, now: datetime, limit: int) -> None:
        reset = resets_at(now)
        super().__init__(
            429,
            "quota-exceeded",
            "Limite diário atingido",
            "Você atingiu o limite diário. Ele renova às 00:00 (horário de Brasília).",
            resets_at=reset.isoformat(),
            limit=limit,
        )
        self.headers = {
            "Retry-After": str(max(1, math.ceil((reset - datetime.now(UTC)).total_seconds())))
        }


class RateLimitedError(ApiProblemError):
    def __init__(self, retry_after: int) -> None:
        super().__init__(
            429,
            "rate-limited",
            "Muitas mensagens",
            f"Muitas mensagens seguidas. Aguarde {retry_after} s e tente de novo.",
            retry_after=retry_after,
        )
        self.headers = {"Retry-After": str(retry_after)}


class DayUsage(BaseModel):
    day: str
    messages: int


class UsageOut(BaseModel):
    messages_today: int
    message_limit: int
    tokens_today: int
    token_limit: int
    resets_at: datetime
    # Do mais antigo a hoje, sempre 7 dias (zeros incluídos).
    last_7_days: list[DayUsage]


def _tokens(doc: dict[str, Any]) -> int:
    return int(doc.get("inputTokens", 0)) + int(doc.get("outputTokens", 0))


class UsageService:
    def __init__(
        self,
        store: UsageStore,
        limits: UsageLimits,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._limits = limits
        self._clock = clock or (lambda: datetime.now(UTC))

    async def reserve(self, uid: str) -> None:
        """Conta a mensagem ou recusa com 429 (`rate-limited` antes de `quota-exceeded`: a
        mensagem recusada pelo rate limit não gasta cota)."""
        now = self._clock()
        limits = self._limits

        def decide(doc: dict[str, Any]) -> tuple[dict[str, Any] | None, Any]:
            recent = sorted(
                t for t in (_aware(x) for x in doc.get("recent") or []) if t > now - WINDOW
            )
            if len(recent) >= limits.rate_limit_per_minute:
                wait = recent[-limits.rate_limit_per_minute] + WINDOW - now
                return None, ("rate", max(1, math.ceil(wait.total_seconds())))
            if int(doc.get("messages", 0)) >= limits.daily_message_quota:
                return None, ("quota", limits.daily_message_quota)
            if _tokens(doc) >= limits.daily_token_quota:
                return None, ("quota", limits.daily_message_quota)
            change = {
                "messages": int(doc.get("messages", 0)) + 1,
                "recent": [*recent, now][-limits.rate_limit_per_minute :],
            }
            return change, None

        try:
            refused = await in_thread(self._store.update_usage, uid, usage_day(now), decide)
        except UsageConflictError:
            refused = ("rate", 1)  # rajada simultânea: tente de novo em 1 s
        if refused is None:
            return
        kind, value = refused
        log.info(  # métrica de limites atingidos (F11-RT-03)
            "usage_limit",
            extra={
                "fields": {
                    "event": "usage_limit",
                    "uid_hash": uid_hash(uid),
                    "limit": "rate-limited" if kind == "rate" else "quota-exceeded",
                }
            },
        )
        if kind == "rate":
            raise RateLimitedError(value)
        raise QuotaExceededError(now, value)

    async def usage(self, uid: str) -> UsageOut:
        now = self._clock()
        today = now.astimezone(BRASILIA).date()
        days = [(today - timedelta(days=n)).isoformat() for n in range(HISTORY_DAYS - 1, -1, -1)]
        docs = await in_thread(self._store.usage_days, uid, days)
        current = docs.get(days[-1], {})
        return UsageOut(
            messages_today=int(current.get("messages", 0)),
            message_limit=self._limits.daily_message_quota,
            tokens_today=_tokens(current),
            token_limit=self._limits.daily_token_quota,
            resets_at=resets_at(now),
            last_7_days=[
                DayUsage(day=d, messages=int(docs.get(d, {}).get("messages", 0))) for d in days
            ],
        )


def _aware(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.combine(date.min, time.min, UTC)  # valor estranho: fica fora da janela
