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
    """O Jira recusou a requisição (400), por exemplo uma JQL inválida; a mensagem é a do Jira.

    `errors` traz os erros por campo (`{"priority": "..."}`), usados para traduzir a falha."""

    def __init__(self, message: str, errors: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or {}


class JiraForbiddenError(JiraError):
    """Numa escrita, 403: a conta não tem permissão para criar/editar ali (a credencial vale)."""


class JiraRateLimitedError(JiraError):
    """O Jira continuou respondendo 429 depois das tentativas; nada foi gravado."""


class JiraUncertainError(JiraError):
    """A escrita foi enviada, mas a resposta não veio (timeout, 5xx): o Jira pode ter gravado."""


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
    id: str = ""
    avatar_url: str | None = None
    # `expand=insight` (F09-RT-01); `None` quando o Jira não manda.
    total_issues: int | None = None


@dataclass(frozen=True)
class JiraStatus:
    name: str  # no idioma do site ("A fazer")
    category: str  # new, indeterminate, done


@dataclass(frozen=True)
class JiraIssueType:
    id: str
    name: str
    hierarchy_level: int  # 1: épico, 0: história/tarefa, -1: subtarefa
    subtask: bool


@dataclass(frozen=True)
class JiraCreated:
    key: str
    url: str


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


MAX_PROJECT_PAGES = 20  # 1000 projetos (F09-RT-03)
ISSUE_FIELDS = ["summary", "description", "issuetype", "status", "priority", "labels", "parent"]
MAX_SEARCH = 50


def _error_detail(response: httpx.Response) -> tuple[list[str], dict[str, str]]:
    try:
        data = response.json()
    except ValueError:
        return [], {}
    if not isinstance(data, dict):
        return [], {}
    errors = data.get("errors") or {}
    return (
        [str(m)[:300] for m in data.get("errorMessages", [])][:10],
        {str(k)[:50]: str(v)[:300] for k, v in errors.items()} if isinstance(errors, dict) else {},
    )


def _error_messages(response: httpx.Response) -> str:
    messages, errors = _error_detail(response)
    joined = [*messages, *(f"{k}: {v}" for k, v in errors.items())]
    return "; ".join(joined)[:500] or f"o Jira respondeu {response.status_code}"


def _name(value: Any) -> str | None:
    return str(value["name"]) if isinstance(value, dict) and value.get("name") else None


def _project(data: dict[str, Any]) -> JiraProject:
    insight = data.get("insight") if isinstance(data.get("insight"), dict) else {}
    total = insight.get("totalIssueCount") if insight else None
    avatars = data.get("avatarUrls") if isinstance(data.get("avatarUrls"), dict) else {}
    avatar = avatars.get("48x48") if avatars else None
    return JiraProject(
        key=str(data["key"]),
        name=str(data.get("name") or ""),
        type=str(data.get("projectTypeKey") or ""),
        id=str(data.get("id") or ""),
        avatar_url=str(avatar)
        if isinstance(avatar, str) and avatar.startswith("https://")
        else None,
        total_issues=int(total) if isinstance(total, int) else None,
    )


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

    async def _write(self, method: str, path: str, body: dict[str, Any]) -> httpx.Response:
        """Escrita (F06): nunca repete depois de enviada, porque o Jira pode ter gravado e uma
        segunda criação duplicaria a issue. Só 429 (não processado) é repetido."""
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = await self._http.request(method, path, json=body)
            except (httpx.ConnectError, httpx.ConnectTimeout):
                raise JiraUnreachableError(f"sem resposta de {self.site_url}") from None
            except httpx.TransportError:
                raise JiraUncertainError("o Jira não respondeu a tempo") from None
            status = response.status_code
            if status == 429:
                if attempt + 1 < MAX_ATTEMPTS:
                    await self._sleep(_retry_after(response, attempt))
                    continue
                raise JiraRateLimitedError("o Jira está limitando as requisições")
            if status == 401:
                raise JiraAuthError("o Jira respondeu 401")
            if status == 403:
                raise JiraForbiddenError(_error_messages(response))
            if status == 404:
                raise JiraNotFoundError("não encontrado no Jira")
            if status == 400:
                raise JiraBadRequestError(_error_messages(response), _error_detail(response)[1])
            if status >= 500:
                raise JiraUncertainError(f"o Jira respondeu {status}")
            if status >= 300:
                raise JiraError(f"o Jira respondeu {status}")
            return response
        raise AssertionError("inalcançável")  # pragma: no cover

    async def project_issue_types(self, project_key: str) -> list[JiraIssueType]:
        """Tipos que o projeto aceita na criação, com os nomes do site (podem estar em
        português: "História", "Tarefa"). `GET /rest/api/3/issue/createmeta/{key}/issuetypes`."""
        response = await self._request(
            "GET",
            f"/rest/api/3/issue/createmeta/{project_key}/issuetypes",
            params={"maxResults": MAX_SEARCH},
            not_found=True,
        )
        return [
            JiraIssueType(
                str(t["id"]),
                str(t.get("name") or ""),
                int(t.get("hierarchyLevel") or 0),
                bool(t.get("subtask")),
            )
            for t in response.json().get("issueTypes", [])
        ]

    async def create_issue(self, fields: dict[str, Any]) -> JiraCreated:
        """`POST /rest/api/3/issue` com os campos já derivados da ação confirmada (F06-RF-02)."""
        response = await self._write("POST", "/rest/api/3/issue", {"fields": fields})
        key = str(response.json()["key"])
        return JiraCreated(key, f"{self.site_url}/browse/{key}")

    async def update_issue(self, key: str, fields: dict[str, Any]) -> None:
        """`PUT /rest/api/3/issue/{key}` só com os campos permitidos (F06-RF-06, D06)."""
        await self._write("PUT", f"/rest/api/3/issue/{key}", {"fields": fields})

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

    async def list_projects(
        self, *, insight: bool = False, max_pages: int = 1
    ) -> list[JiraProject]:
        """`GET /rest/api/3/project/search`: projetos visíveis para a conta, 50 por página, até
        `isLast` ou `max_pages` (F09-RT-03). Com `insight`, cada projeto traz o total de issues."""
        projects: list[JiraProject] = []
        for page in range(max_pages):
            params: dict[str, Any] = {"startAt": page * MAX_SEARCH, "maxResults": MAX_SEARCH}
            if insight:
                params["expand"] = "insight"
            data = (await self._request("GET", "/rest/api/3/project/search", params=params)).json()
            values = data.get("values") or []
            projects.extend(_project(p) for p in values)
            if data.get("isLast", True) or not values:
                break
        return projects

    async def approximate_count(self, jql: str) -> int:
        """`POST /rest/api/3/search/approximate-count`: quantas issues a JQL encontra."""
        response = await self._request(
            "POST", "/rest/api/3/search/approximate-count", json={"jql": jql}
        )
        return int(response.json()["count"])

    async def statuses(self, keys: list[str]) -> dict[str, JiraStatus]:
        """`POST /rest/api/3/issue/bulkfetch` (até 100): status atual de cada chave. As que não
        existem mais (ou que a conta não vê) simplesmente não voltam (F10-RF-05)."""
        if not keys:
            return {}
        response = await self._request(
            "POST",
            "/rest/api/3/issue/bulkfetch",
            json={"issueIdsOrKeys": keys[:100], "fields": ["status"]},
        )
        found: dict[str, JiraStatus] = {}
        for issue in response.json().get("issues") or []:
            status = (issue.get("fields") or {}).get("status") or {}
            category = (status.get("statusCategory") or {}).get("key") or ""
            found[str(issue["key"])] = JiraStatus(str(status.get("name") or ""), str(category))
        return found

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
