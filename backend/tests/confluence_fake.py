"""Confluence Cloud simulado (respx) e leitor em memória para os testes da F19."""

from typing import Any

import httpx
import respx

from app.agent.tools.context import ConfluenceToolError, DocPage, DocSpace
from tests.jira_fake import SITE

WIKI = f"{SITE}/wiki"
SPACE = {
    "id": "65801",
    "key": "SCRUM",
    "name": "Minha equipe",
    "homepageId": "65914",
    "_links": {"webui": "/spaces/SCRUM"},
}
RULES_STORAGE = (
    "<h2>Regras</h2><table><tbody><tr><th>ID</th><th>Regra</th></tr>"
    "<tr><td>RN-03</td><td>Pedido acima de R$ 1.000 exige aprovação</td></tr></tbody></table>"
)


def page_json(page_id: str, title: str, storage: str, space_id: str = "65801") -> dict[str, Any]:
    return {
        "id": page_id,
        "title": title,
        "spaceId": space_id,
        "version": {"number": 3},
        "body": {"storage": {"value": storage}},
        "_links": {"webui": f"/spaces/SCRUM/pages/{page_id}"},
    }


def search_json(*pages: tuple[str, str, list[str]]) -> dict[str, Any]:
    return {
        "results": [
            {
                "content": {
                    "id": pid,
                    "type": "page",
                    "title": title,
                    "metadata": {"labels": {"results": [{"name": lb} for lb in labels]}},
                    "_links": {"webui": f"/spaces/SCRUM/pages/{pid}"},
                },
                "excerpt": f"trecho de {title}",
            }
            for pid, title, labels in pages
        ]
    }


def spaces(router: respx.MockRouter, *found: dict[str, Any]) -> respx.Route:
    """`GET /wiki/api/v2/spaces`: filtra por `keys` como o Confluence."""

    def handler(request: httpx.Request) -> httpx.Response:
        keys = request.url.params.get("keys")
        items = [s for s in found if not keys or s["key"] == keys]
        return httpx.Response(200, json={"results": items, "_links": {}})

    return router.get(f"{WIKI}/api/v2/spaces").mock(side_effect=handler)


class FakeConfluenceReader:
    """`ConfluenceReader` em memória (ferramentas e chat)."""

    def __init__(self, pages: dict[str, DocPage] | None = None, *, fail: bool = False) -> None:
        self.space = DocSpace("SCRUM", "Minha equipe", f"{WIKI}/spaces/SCRUM", SITE)
        self.pages = pages or {
            "101": DocPage(
                "101",
                "Regras de negócio",
                f"{WIKI}/spaces/SCRUM/pages/101",
                "regras",
                "",
                "| ID | Regra |\n|---|---|\n| RN-03 | Pedido acima de R$ 1.000 exige aprovação |",
            ),
            "102": DocPage(
                "102",
                "Constituição",
                f"{WIKI}/spaces/SCRUM/pages/102",
                "constituicao",
                "",
                "### Art. I. Dados no Brasil\n1. Dados de clientes MUST ficar no Brasil.",
            ),
        }
        self.fail = fail
        self.searches: list[str] = []

    async def index(self) -> list[DocPage]:
        if self.fail:
            raise ConfluenceToolError("a conta não tem acesso a este espaço do Confluence")
        return [DocPage(p.id, p.title, p.url, p.kind) for p in self.pages.values()]

    async def search(self, text: str, limit: int) -> list[DocPage]:
        self.searches.append(text)
        return [
            DocPage(p.id, p.title, p.url, p.kind, p.markdown[:80])
            for p in self.pages.values()
            if text.lower() in (p.title + p.markdown).lower()
        ][:limit]

    async def page(self, page_id: str) -> DocPage:
        if page_id not in self.pages:
            raise ConfluenceToolError("página não encontrada neste espaço")
        return self.pages[page_id]
