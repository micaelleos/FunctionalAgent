"""Cliente HTTP do Confluence Cloud, só leitura (F19-RT-01, ADR-009).

Mesma credencial e mesmo host da conexão Atlassian da F04 (`https://<site>.atlassian.net`, com o
Confluence em `/wiki`): o guard de SSRF (`normalize_site_url`) vale igual. Uma instância por
requisição; o token vive só aqui. Redirecionamentos não são seguidos (a credencial não sai do host).
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
MAX_SPACES = 250
MAX_SEARCH = 25


class ConfluenceError(Exception):
    """Erro ao falar com o Confluence. Mensagens nunca incluem o token."""


class ConfluenceAuthError(ConfluenceError):
    """401/403: credencial recusada ou a conta não tem acesso ao Confluence (ou ao espaço)."""


class ConfluenceNotFoundError(ConfluenceError):
    """Espaço ou página inexistente, ou sem permissão de leitura (o Confluence responde 404)."""


class ConfluenceBadRequestError(ConfluenceError):
    """400: por exemplo uma CQL inválida."""


class ConfluenceUnreachableError(ConfluenceError):
    """Fora do ar, lento demais, 3xx ou 5xx depois das tentativas."""


@dataclass(frozen=True)
class ConfluenceSpace:
    id: str
    key: str
    name: str
    url: str
    homepage_id: str | None = None


@dataclass(frozen=True)
class ConfluencePageRef:
    id: str
    title: str
    url: str
    labels: tuple[str, ...] = ()
    excerpt: str = ""


@dataclass(frozen=True)
class ConfluencePage:
    id: str
    title: str
    url: str
    space_id: str
    storage: str  # corpo em storage format (XHTML)
    version: int


def _backoff(attempt: int) -> float:
    return min(0.5 * float(2**attempt), MAX_RETRY_AFTER)


def _retry_after(response: httpx.Response, attempt: int) -> float:
    header = response.headers.get("Retry-After")
    if header:
        with contextlib.suppress(ValueError):
            return float(min(max(float(header), 0.0), MAX_RETRY_AFTER))
    return _backoff(attempt)


def cql_string(value: str) -> str:
    """Literal de CQL entre aspas, com aspas e barras escapadas (F19-RT-03)."""
    cleaned = " ".join(value.replace("\\", " ").split())[:200]
    return '"' + cleaned.replace('"', '\\"') + '"'


class ConfluenceClient:
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
        self.wiki_url = f"{self.site_url}/wiki"
        self._sleep = sleep
        self._http = httpx.AsyncClient(
            base_url=self.wiki_url,
            auth=httpx.BasicAuth(email, api_token),
            timeout=TIMEOUT,
            follow_redirects=False,
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

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = await self._http.get(path, params=params)
            except httpx.TransportError as exc:
                if attempt + 1 < MAX_ATTEMPTS and isinstance(exc, httpx.TimeoutException):
                    await self._sleep(_backoff(attempt))
                    continue
                raise ConfluenceUnreachableError("sem resposta do Confluence") from None
            if response.status_code in _RETRY_STATUS and attempt + 1 < MAX_ATTEMPTS:
                await self._sleep(_retry_after(response, attempt))
                continue
            status = response.status_code
            if status in {401, 403}:
                raise ConfluenceAuthError(f"o Confluence respondeu {status}")
            if status == 404:
                raise ConfluenceNotFoundError("não encontrado no Confluence")
            if status == 400:
                raise ConfluenceBadRequestError("o Confluence recusou a consulta")
            if status >= 300:
                raise ConfluenceUnreachableError(f"o Confluence respondeu {status}")
            try:
                data = response.json()
            except ValueError:
                raise ConfluenceUnreachableError("resposta inválida do Confluence") from None
            return data if isinstance(data, dict) else {}
        raise AssertionError("inalcançável")  # pragma: no cover

    def _url(self, webui: Any) -> str:
        path = str(webui or "")
        return f"{self.wiki_url}{path}" if path.startswith("/") else self.wiki_url

    def _space(self, data: dict[str, Any]) -> ConfluenceSpace:
        links = data.get("_links") if isinstance(data.get("_links"), dict) else {}
        homepage = data.get("homepageId")
        return ConfluenceSpace(
            id=str(data.get("id") or ""),
            key=str(data.get("key") or ""),
            name=str(data.get("name") or ""),
            url=self._url((links or {}).get("webui")),
            homepage_id=str(homepage) if homepage else None,
        )

    async def space_by_key(self, key: str) -> ConfluenceSpace | None:
        data = await self._get("/api/v2/spaces", {"keys": key, "limit": 1})
        results = [r for r in data.get("results", []) if isinstance(r, dict)]
        return self._space(results[0]) if results else None

    async def space_by_id(self, space_id: str) -> ConfluenceSpace:
        if not space_id.isdigit():
            raise ConfluenceNotFoundError("espaço inválido")
        return self._space(await self._get(f"/api/v2/spaces/{space_id}"))

    async def list_spaces(self) -> list[ConfluenceSpace]:
        """Espaços visíveis para a conta (até 250, sem os pessoais)."""
        spaces: list[ConfluenceSpace] = []
        params: dict[str, Any] = {"limit": 250, "type": "global", "status": "current"}
        cursor: str | None = None
        while len(spaces) < MAX_SPACES:
            page_params = {**params, **({"cursor": cursor} if cursor else {})}
            data = await self._get("/api/v2/spaces", page_params)
            spaces += [self._space(r) for r in data.get("results", []) if isinstance(r, dict)]
            next_link = str(((data.get("_links") or {}).get("next")) or "")
            if "cursor=" not in next_link:
                break
            cursor = httpx.URL(next_link).params.get("cursor")
            if not cursor:
                break
        return spaces[:MAX_SPACES]

    async def search(self, cql: str, limit: int = 10) -> list[ConfluencePageRef]:
        """Busca CQL (v1; a v2 não tem busca). A CQL vem sempre montada pelo código (RT-03)."""
        data = await self._get(
            "/rest/api/search",
            {
                "cql": cql,
                "limit": max(1, min(limit, MAX_SEARCH)),
                "expand": "content.metadata.labels",
            },
        )
        pages: list[ConfluencePageRef] = []
        for item in data.get("results", []):
            content = item.get("content") if isinstance(item, dict) else None
            if not isinstance(content, dict) or content.get("type") != "page":
                continue
            labels = (((content.get("metadata") or {}).get("labels") or {}).get("results")) or []
            links = content.get("_links") if isinstance(content.get("_links"), dict) else {}
            pages.append(
                ConfluencePageRef(
                    id=str(content.get("id") or ""),
                    title=str(content.get("title") or ""),
                    url=self._url((links or {}).get("webui")),
                    labels=tuple(str(lb.get("name")) for lb in labels if isinstance(lb, dict)),
                    excerpt=str(item.get("excerpt") or "")[:300],
                )
            )
        return pages

    async def page_space_id(self, page_id: str) -> str:
        """Espaço de uma página (descoberta pelo rótulo, F19-RF-01)."""
        if not page_id.isdigit():
            raise ConfluenceNotFoundError("página inválida")
        data = await self._get(f"/api/v2/pages/{page_id}")
        return str(data.get("spaceId") or "")

    async def page(self, page_id: str) -> ConfluencePage:
        if not page_id.isdigit():
            raise ConfluenceNotFoundError("página inválida")
        data = await self._get(f"/api/v2/pages/{page_id}", {"body-format": "storage"})
        body = ((data.get("body") or {}).get("storage") or {}).get("value") or ""
        links = data.get("_links") if isinstance(data.get("_links"), dict) else {}
        version = (data.get("version") or {}).get("number") or 0
        return ConfluencePage(
            id=str(data.get("id") or page_id),
            title=str(data.get("title") or ""),
            url=self._url((links or {}).get("webui")),
            space_id=str(data.get("spaceId") or ""),
            storage=str(body),
            version=int(version) if isinstance(version, int) else 0,
        )
