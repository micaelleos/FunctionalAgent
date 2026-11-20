"""Adapta o `ConfluenceClient` do usuário à interface `ConfluenceReader` do agente (F19-RT-02).

Restringe tudo ao espaço vinculado: a CQL é montada aqui com a chave do espaço e o termo escapado
(F19-RT-03), e uma página de outro espaço não é devolvida. Erros do Confluence nunca marcam a
conexão do Jira como inválida (F19-RF-09): a mesma credencial pode valer para o Jira e não ter
acesso ao Confluence.
"""

import logging
import time

from app.agent.tools.context import ConfluenceToolError, DocPage, DocSpace
from app.core.logging import uid_hash
from app.integrations.confluence.client import (
    ConfluenceAuthError,
    ConfluenceClient,
    ConfluenceError,
    ConfluenceNotFoundError,
    ConfluencePageRef,
    ConfluenceSpace,
    cql_string,
)
from app.integrations.confluence.markdown import storage_to_markdown

log = logging.getLogger("app.confluence")

# Tipos da metodologia (docs/metodologia/espaco-confluence.md §2): rótulo e título do modelo.
KINDS = {
    "inicio": "Início",
    "constituicao": "Constituição",
    "glossario": "Glossário",
    "regras": "Regras de negócio",
    "arquitetura": "Arquitetura",
    "adr": "Decisões (ADR)",
    "roadmap": "Roadmap",
    "feature": "Features",
    "registro": "Registro de mudanças",
}
_TITLE_KIND = {title.lower(): kind for kind, title in KINDS.items()}
LABEL_PREFIX = "specflow-tipo-"
INDEX_LIMIT = 25


def index_cql(space_key: str) -> str:
    labels = ", ".join(cql_string(f"{LABEL_PREFIX}{k}") for k in KINDS)
    titles = ", ".join(cql_string(t) for t in KINDS.values())
    return (
        f"space = {cql_string(space_key)} AND type = page AND "
        f'(label in ({labels}) OR title in ({titles}) OR title ~ "ADR")'
    )


def search_cql(space_key: str, text: str) -> str:
    return f"space = {cql_string(space_key)} AND type = page AND text ~ {cql_string(text)}"


def kind_of(title: str, labels: tuple[str, ...]) -> str:
    for label in labels:
        if label.startswith(LABEL_PREFIX) and label[len(LABEL_PREFIX) :] in KINDS:
            return label[len(LABEL_PREFIX) :]
    lowered = title.strip().lower()
    if lowered in _TITLE_KIND:
        return _TITLE_KIND[lowered]
    return "adr" if lowered.startswith("adr-") else ""


def _doc(ref: ConfluencePageRef) -> DocPage:
    return DocPage(ref.id, ref.title, ref.url, kind_of(ref.title, ref.labels), ref.excerpt)


class ConfluenceReaderAdapter:
    def __init__(self, client: ConfluenceClient, space: ConfluenceSpace, uid: str) -> None:
        self._client = client
        self._space_id = space.id
        self._uid = uid
        self.space = DocSpace(space.key, space.name, space.url, client.site_url)

    def _fail(self, exc: ConfluenceError) -> ConfluenceToolError:
        if isinstance(exc, ConfluenceAuthError):
            return ConfluenceToolError("a conta não tem acesso a este espaço do Confluence")
        if isinstance(exc, ConfluenceNotFoundError):
            return ConfluenceToolError("página não encontrada neste espaço")
        return ConfluenceToolError("o Confluence não respondeu; tente de novo em instantes")

    def _log(self, tool: str, pages: int, started: float) -> None:
        # Métrica de leitura (F19-RT-12): nunca título nem conteúdo.
        log.info(
            "confluence_read",
            extra={
                "fields": {
                    "event": "confluence_read",
                    "uid_hash": uid_hash(self._uid),
                    "tool": tool,
                    "pages": pages,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                }
            },
        )

    async def index(self) -> list[DocPage]:
        started = time.monotonic()
        try:
            refs = await self._client.search(index_cql(self.space.key), INDEX_LIMIT)
        except ConfluenceError as exc:
            raise self._fail(exc) from None
        pages = [_doc(r) for r in refs]
        order = list(KINDS)
        pages.sort(key=lambda p: (order.index(p.kind) if p.kind in order else len(order), p.title))
        self._log("index", len(pages), started)
        return pages

    async def search(self, text: str, limit: int) -> list[DocPage]:
        started = time.monotonic()
        try:
            refs = await self._client.search(search_cql(self.space.key, text), limit)
        except ConfluenceError as exc:
            raise self._fail(exc) from None
        self._log("search", len(refs), started)
        return [_doc(r) for r in refs]

    async def page(self, page_id: str) -> DocPage:
        started = time.monotonic()
        try:
            page = await self._client.page(page_id)
        except ConfluenceError as exc:
            raise self._fail(exc) from None
        if page.space_id and page.space_id != self._space_id:
            raise ConfluenceToolError("a página não é do espaço vinculado a este projeto")
        self._log("page", 1, started)
        return DocPage(
            page.id,
            page.title,
            page.url,
            kind_of(page.title, ()),
            "",
            storage_to_markdown(page.storage),
        )
