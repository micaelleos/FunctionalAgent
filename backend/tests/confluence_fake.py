"""Confluence Cloud simulado (respx) e leitor em memória para os testes da F19."""

import json
import re
from typing import Any

import httpx
import respx

from app.agent.tools.context import ConfluenceToolError, DocPage, DocSpace
from app.integrations.confluence.client import ConfluenceClient
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


class FakeWiki:
    """Confluence em memória atrás de um `httpx.MockTransport` (F20): espaços, páginas com versão
    (409 se a versão não for a atual + 1), rótulos e uma busca CQL simplificada."""

    def __init__(self) -> None:
        self.spaces: dict[str, dict[str, Any]] = {}
        self.pages: dict[str, dict[str, Any]] = {}
        self.writes: list[httpx.Request] = []
        self.fail_on: dict[tuple[str, str], int] = {}  # (método, sufixo do caminho) → status
        self.fail_create_after: int | None = None  # nº de criações de página antes de falhar
        self._next = 900

    def _id(self) -> str:
        self._next += 1
        return str(self._next)

    def add_space(self, key: str = "SCRUM", name: str = "Minha equipe") -> dict[str, Any]:
        space_id, home = self._id(), self._id()
        space = {
            "id": space_id,
            "key": key,
            "name": name,
            "homepageId": home,
            "_links": {"webui": f"/spaces/{key}"},
        }
        self.spaces[key] = space
        self.pages[home] = self._page(home, f"{name} Home", "<p>home</p>", space_id, key)
        return space

    def _page(
        self, page_id: str, title: str, storage: str, space_id: str, key: str, labels: Any = ()
    ) -> dict[str, Any]:
        return {
            "id": page_id,
            "title": title,
            "storage": storage,
            "spaceId": space_id,
            "spaceKey": key,
            "version": 1,
            "labels": list(labels),
        }

    def add_page(
        self, title: str, storage: str, labels: list[str], key: str = "SCRUM", version: int = 1
    ) -> str:
        space = self.spaces[key]
        page_id = self._id()
        self.pages[page_id] = self._page(page_id, title, storage, space["id"], key, labels)
        self.pages[page_id]["version"] = version
        return page_id

    def _json(self, page: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": page["id"],
            "title": page["title"],
            "spaceId": page["spaceId"],
            "version": {"number": page["version"]},
            "body": {"storage": {"value": page["storage"]}},
            "_links": {"webui": f"/spaces/{page['spaceKey']}/pages/{page['id']}"},
        }

    def _search(self, cql: str) -> list[dict[str, Any]]:
        key = re.search(r'space = "([^"]+)"', cql)
        pages = [p for p in self.pages.values() if not key or p["spaceKey"] == key[1]]
        exact = re.findall(r'title = "([^"]+)"', cql)
        contains = re.findall(r'title ~ "([^"]+)"', cql)
        labels = re.findall(r'label = "([^"]+)"', cql)
        if "label in" in cql:  # índice da F19
            return [
                p
                for p in pages
                if any(lb.startswith("specflow-tipo-") for lb in p["labels"])
                or p["title"].startswith("ADR")
            ]
        if exact or labels:
            return [p for p in pages if p["title"] in exact or set(labels) & set(p["labels"])]
        if contains:
            return [p for p in pages if any(c.lower() in p["title"].lower() for c in contains)]
        return pages

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path.removeprefix("/wiki"), request.method
        for (m, suffix), status in self.fail_on.items():
            if m == method and path.endswith(suffix):
                return httpx.Response(status, json={})
        if method != "GET":
            self.writes.append(request)
        body: Any = json.loads(request.content) if request.content else {}
        if method == "GET" and path == "/api/v2/spaces":
            key = request.url.params.get("keys")
            found = [s for k, s in self.spaces.items() if k == key]
            return httpx.Response(200, json={"results": found, "_links": {}})
        if method == "POST" and path == "/rest/api/space":
            if body["key"] in self.spaces:
                return httpx.Response(400, json={"message": "A space with key exists"})
            self.add_space(body["key"], body["name"])
            return httpx.Response(200, json={"key": body["key"]})
        if method == "GET" and path == "/rest/api/search":
            found = self._search(request.url.params["cql"])
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "content": {
                                "id": p["id"],
                                "type": "page",
                                "title": p["title"],
                                "metadata": {
                                    "labels": {"results": [{"name": lb} for lb in p["labels"]]}
                                },
                                "_links": {"webui": f"/spaces/{p['spaceKey']}/pages/{p['id']}"},
                            }
                        }
                        for p in found
                    ]
                },
            )
        match = re.fullmatch(r"/api/v2/pages/(\d+)", path)
        if match and method == "GET":
            page = self.pages.get(match[1])
            return httpx.Response(200, json=self._json(page)) if page else httpx.Response(404)
        if match and method == "PUT":
            page = self.pages[match[1]]
            if body["version"]["number"] != page["version"] + 1:
                return httpx.Response(409, json={"message": "Version must be incremented"})
            page.update(
                title=body["title"],
                storage=body["body"]["value"],
                version=body["version"]["number"],
            )
            return httpx.Response(200, json=self._json(page))
        if method == "POST" and path == "/api/v2/pages":
            creations = sum(1 for r in self.writes if r.url.path.endswith("/api/v2/pages"))
            if self.fail_create_after is not None and creations > self.fail_create_after:
                return httpx.Response(503)
            space = next(s for s in self.spaces.values() if s["id"] == body["spaceId"])
            if any(
                p["title"] == body["title"] and p["spaceId"] == body["spaceId"]
                for p in self.pages.values()
            ):
                return httpx.Response(
                    400, json={"message": "A page with this title already exists"}
                )
            page_id = self._id()
            page = self._page(
                page_id, body["title"], body["body"]["value"], space["id"], space["key"]
            )
            page["parentId"] = body.get("parentId")
            self.pages[page_id] = page
            return httpx.Response(200, json=self._json(page))
        label = re.fullmatch(r"/rest/api/content/(\d+)/label", path)
        if label and method == "POST":
            self.pages[label[1]]["labels"].extend(item["name"] for item in body)
            return httpx.Response(200, json={})
        return httpx.Response(404)

    def client(self) -> ConfluenceClient:
        return ConfluenceClient(SITE, "po@teste.dev", "x" * 12, transport=httpx.MockTransport(self))

    def by_title(self, title: str) -> dict[str, Any]:
        return next(p for p in self.pages.values() if p["title"] == title)
