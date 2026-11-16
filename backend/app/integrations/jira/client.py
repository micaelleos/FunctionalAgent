"""Cliente HTTP do Jira Cloud com API token (ADR-004, F04-RT-03, F04-RT-04).

Uma instância por requisição e por usuário: o token chega decifrado do serviço, vive só aqui e não é
guardado em nenhum cache global (F04-RT-05). F05, F09 e F10 acrescentam os métodos que usam.
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Self

import httpx

from app.integrations.jira.urls import normalize_site_url

TIMEOUT = httpx.Timeout(20.0, connect=5.0)
MAX_ATTEMPTS = 3
MAX_RETRY_AFTER = 10.0
_RETRY_STATUS = {429, 500, 502, 503, 504}


class JiraError(Exception):
    """Erro ao falar com o Jira. Mensagens nunca incluem o token."""


class JiraAuthError(JiraError):
    """O Jira recusou e-mail/token (401) ou a conta não tem acesso ao site (403)."""


class JiraUnreachableError(JiraError):
    """Site inexistente, fora do ar, lento demais ou respondendo erro depois das tentativas."""


@dataclass(frozen=True)
class JiraAccount:
    account_id: str
    display_name: str
    email: str | None


def _backoff(attempt: int) -> float:
    return min(0.5 * float(2**attempt), MAX_RETRY_AFTER)


def _retry_after(response: httpx.Response, attempt: int) -> float:
    """Espera antes da próxima tentativa: `Retry-After` em segundos (limitado) ou backoff."""
    header = response.headers.get("Retry-After")
    if header:
        with contextlib.suppress(ValueError):
            return float(min(max(float(header), 0.0), MAX_RETRY_AFTER))
    return _backoff(attempt)


class JiraClient:
    def __init__(
        self,
        site_url: str,
        email: str,
        api_token: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.site_url = normalize_site_url(site_url)
        self._sleep = sleep
        self._http = httpx.AsyncClient(
            base_url=self.site_url,
            auth=httpx.BasicAuth(email, api_token),
            timeout=TIMEOUT,
            follow_redirects=False,  # um 3xx poderia levar a credencial para outro host
            headers={"Accept": "application/json"},
            transport=transport,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = await self._http.request(method, path, **kwargs)
            except httpx.TransportError as exc:
                if attempt + 1 < MAX_ATTEMPTS and isinstance(exc, httpx.TimeoutException):
                    await self._sleep(_backoff(attempt))
                    continue
                raise JiraUnreachableError(f"sem resposta de {self.site_url}") from None
            if response.status_code in _RETRY_STATUS and attempt + 1 < MAX_ATTEMPTS:
                await self._sleep(_retry_after(response, attempt))
                continue
            return self._check(response)
        raise AssertionError("inalcançável")  # pragma: no cover

    def _check(self, response: httpx.Response) -> httpx.Response:
        status = response.status_code
        if status in {401, 403}:
            raise JiraAuthError(f"o Jira respondeu {status}")
        if 300 <= status < 400 or status == 404 or status >= 500 or status == 429:
            # 404 em /myself: não é um site Jira (ou foi desativado); 3xx: não seguimos.
            raise JiraUnreachableError(f"o Jira respondeu {status}")
        if status >= 400:
            raise JiraError(f"o Jira respondeu {status}")
        return response

    async def myself(self) -> JiraAccount:
        """`GET /rest/api/3/myself`: valida a credencial e devolve a conta (F04-RF-02)."""
        data = (await self._request("GET", "/rest/api/3/myself")).json()
        return JiraAccount(
            account_id=str(data["accountId"]),
            display_name=str(data.get("displayName") or data.get("emailAddress") or ""),
            email=data.get("emailAddress"),
        )
