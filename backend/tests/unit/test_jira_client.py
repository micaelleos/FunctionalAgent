"""Cliente Jira (F04-RT-03, F04-RT-04) contra um Jira simulado (respx)."""

import httpx
import pytest
import respx

from app.integrations.jira.client import (
    TIMEOUT,
    JiraAuthError,
    JiraClient,
    JiraError,
    JiraUnreachableError,
)
from tests.jira_fake import ACCOUNT, EMAIL, SITE, TOKEN, myself

URL = f"{SITE}/rest/api/3/myself"


class Sleeps:
    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def client(sleep: Sleeps | None = None, token: str = TOKEN) -> JiraClient:
    return JiraClient(SITE, EMAIL, token, sleep=sleep or Sleeps())


@respx.mock
async def test_myself_com_basic_auth() -> None:
    route = myself(respx.mock)
    async with client() as jira:
        account = await jira.myself()

    assert account.display_name == ACCOUNT["displayName"]
    assert account.account_id == "acc-1"
    assert route.calls.last.request.headers["Authorization"].startswith("Basic ")


@pytest.mark.req("F04-RF-03")
@respx.mock
async def test_credencial_recusada() -> None:
    myself(respx.mock)
    async with client(token="outro-token-1234") as jira:
        with pytest.raises(JiraAuthError):
            await jira.myself()


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (403, JiraAuthError),
        (404, JiraUnreachableError),
        (302, JiraUnreachableError),
        (400, JiraError),
    ],
)
@respx.mock
async def test_mapeia_status(status: int, error: type[Exception]) -> None:
    respx.get(URL).respond(status, headers={"Location": "https://evil.com"})
    async with client() as jira:
        with pytest.raises(error):
            await jira.myself()


@pytest.mark.req("F04-RT-03")
@respx.mock
async def test_nao_segue_redirecionamento() -> None:
    evil = respx.get("https://evil.com/").respond(200, json=ACCOUNT)
    respx.get(URL).respond(302, headers={"Location": "https://evil.com/"})
    async with client() as jira:
        with pytest.raises(JiraUnreachableError):
            await jira.myself()
    assert not evil.called


@pytest.mark.req("F04-RT-04")
@respx.mock
async def test_429_respeita_retry_after() -> None:
    respx.get(URL).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "2"}),
            httpx.Response(429, headers={"Retry-After": "999"}),
            httpx.Response(200, json=ACCOUNT),
        ]
    )
    sleeps = Sleeps()
    async with client(sleeps) as jira:
        assert (await jira.myself()).account_id == "acc-1"
    assert sleeps.calls == [2.0, 10.0]  # Retry-After limitado a 10 s


@pytest.mark.req("F04-RT-04")
@respx.mock
async def test_5xx_tenta_3_vezes_com_backoff() -> None:
    route = respx.get(URL).respond(503)
    sleeps = Sleeps()
    async with client(sleeps) as jira:
        with pytest.raises(JiraUnreachableError):
            await jira.myself()
    assert route.call_count == 3
    assert sleeps.calls == [0.5, 1.0]


@pytest.mark.req("F04-RT-04")
@respx.mock
async def test_timeout_tenta_de_novo_e_erro_de_conexao_nao() -> None:
    timeout = respx.get(URL).mock(
        side_effect=[httpx.ReadTimeout("lento"), httpx.Response(200, json=ACCOUNT)]
    )
    async with client() as jira:
        await jira.myself()
    assert timeout.call_count == 2

    respx.get(URL).mock(side_effect=httpx.ConnectError("dns"))
    async with client() as jira:
        with pytest.raises(JiraUnreachableError) as exc:
            await jira.myself()
    assert TOKEN not in str(exc.value)


@pytest.mark.req("F04-RT-04")
def test_timeouts() -> None:
    assert TIMEOUT.connect == 5.0
    assert TIMEOUT.read == 20.0
