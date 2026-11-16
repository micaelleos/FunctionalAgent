"""Jira Cloud simulado com respx para os testes da F04."""

import httpx
import respx

SITE = "https://sandbox-teste.atlassian.net"
EMAIL = "po@teste.dev"
TOKEN = "ATATT3xFfGF0-token-de-teste-9876"  # nunca é um token real
ACCOUNT = {"accountId": "acc-1", "displayName": "PO Teste", "emailAddress": EMAIL}


def myself(router: respx.MockRouter, site: str = SITE, *, valid_token: str = TOKEN) -> respx.Route:
    """`/myself` aceita só `EMAIL` + `valid_token`; o resto recebe 401, como o Jira."""

    def handler(request: httpx.Request) -> httpx.Response:
        expected = httpx.BasicAuth(EMAIL, valid_token)
        auth = next(expected.auth_flow(httpx.Request("GET", site))).headers["Authorization"]
        if request.headers.get("Authorization") == auth:
            return httpx.Response(200, json=ACCOUNT)
        return httpx.Response(401, json={"message": "Client must be authenticated"})

    return router.get(f"{site}/rest/api/3/myself").mock(side_effect=handler)
