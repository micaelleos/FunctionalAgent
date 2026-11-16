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


class JiraNotFoundError(JiraError):
    """Issue ou projeto inexistente, ou sem permissão de leitura (o Jira responde 404 nos dois)."""


class JiraBadRequestError(JiraError):
    """O Jira recusou a requisição (400), por exemplo uma JQL inválida; a mensagem é a do Jira."""


@dataclass(frozen=True)
class JiraAccount:
    account_id: str
    display_name: str
    email: str | None


@dataclass(frozen=True)
class JiraProject:
    key: str
    name: str
    type: str


@dataclass(frozen=True)
class JiraIssue:
    key: str
    summary: str
    issue_type: str
    status: str
    priority: str | None
    labels: tuple[str, ...]
    parent_key: str | None
    description: dict[str, Any] | None  # ADF
    url: str


ISSUE_FIELDS = ["summary", "description", "issuetype", "status", "priority", "labels", "parent"]
MAX_SEARCH = 50


def _error_messages(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return "o Jira respondeu 400"
    messages = [str(m) for m in data.get("errorMessages", [])]
    messages += [f"{k}: {v}" for k, v in (data.get("errors") or {}).items()]
    return "; ".join(messages)[:500] or "o Jira respondeu 400"


def _name(value: Any) -> str | None:
    return str(value["name"]) if isinstance(value, dict) and value.get("name") else None


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

    async def _request(
        self, method: str, path: str, *, not_found: bool = False, **kwargs: Any
    ) -> httpx.Response:
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
            return self._check(response, not_found=not_found)
        raise AssertionError("inalcançável")  # pragma: no cover

    def _check(self, response: httpx.Response, *, not_found: bool = False) -> httpx.Response:
        status = response.status_code
        if status in {401, 403}:
            raise JiraAuthError(f"o Jira respondeu {status}")
        if status == 404 and not_found:
            raise JiraNotFoundError("não encontrado no Jira")
        if status == 400:
            raise JiraBadRequestError(_error_messages(response))
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

    def _issue(self, data: dict[str, Any]) -> JiraIssue:
        fields = data.get("fields") or {}
        parent = fields.get("parent")
        description = fields.get("description")
        return JiraIssue(
            key=str(data["key"]),
            summary=str(fields.get("summary") or ""),
            issue_type=_name(fields.get("issuetype")) or "",
            status=_name(fields.get("status")) or "",
            priority=_name(fields.get("priority")),
            labels=tuple(str(label) for label in fields.get("labels") or []),
            parent_key=str(parent["key"])
            if isinstance(parent, dict) and parent.get("key")
            else None,
            description=description if isinstance(description, dict) else None,
            url=f"{self.site_url}/browse/{data['key']}",
        )

    async def list_projects(self) -> list[JiraProject]:
        """`GET /rest/api/3/project/search`: projetos visíveis para a conta (até 50)."""
        response = await self._request(
            "GET", "/rest/api/3/project/search", params={"maxResults": MAX_SEARCH}
        )
        return [
            JiraProject(str(p["key"]), str(p.get("name") or ""), str(p.get("projectTypeKey") or ""))
            for p in response.json().get("values", [])
        ]

    async def get_issue(self, key: str) -> JiraIssue:
        response = await self._request(
            "GET",
            f"/rest/api/3/issue/{key}",
            params={"fields": ",".join(ISSUE_FIELDS)},
            not_found=True,
        )
        return self._issue(response.json())

    async def search(self, jql: str, limit: int = MAX_SEARCH) -> list[JiraIssue]:
        """`POST /rest/api/3/search/jql`, limitado a 50 resultados (F05-RT-04)."""
        body = {"jql": jql, "maxResults": max(1, min(limit, MAX_SEARCH)), "fields": ISSUE_FIELDS}
        response = await self._request("POST", "/rest/api/3/search/jql", json=body)
        return [self._issue(issue) for issue in response.json().get("issues", [])]
