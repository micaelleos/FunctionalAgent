"""Preparação das escritas no Confluence (F20-RF-01..03, F20-RT-03, F20-RT-04, F20-RT-08).

Implementa `DocsWriter` e `SpaceCreator` do agente: valida o pedido do modelo, gera o storage
format, lê a versão atual e calcula o diff. Nada é escrito aqui; a confirmação executa o payload
(`services/confluence_actions.py`). Só no espaço vinculado ao projeto da conversa.
"""

import re
from typing import Any

from app.agent.docs_model import SINGLETONS, SPACE_TREE, WRITABLE, fill, labels_for, template
from app.agent.tools.context import ConfluenceToolError, DocPage, DocSpace, PageDraft
from app.integrations.confluence.client import (
    ConfluenceAuthError,
    ConfluenceClient,
    ConfluenceError,
    ConfluenceNotFoundError,
    ConfluenceSpace,
    cql_string,
)
from app.integrations.confluence.markdown import storage_to_markdown
from app.integrations.confluence.storage import markdown_to_storage
from app.services.confluence_reader import ConfluenceReaderAdapter, kind_of
from app.services.page_diff import section_diff

MAX_STORAGE = 50_000
READ_LIMIT = (
    8000  # o que o agente lê de uma página (F19-RT-04): acima disso, reescrever perde texto
)
FULL = 1_000_000
_NUMBERED = {
    "adr": re.compile(r"^(ADR-\d{3})\s+[\u2014\u2013-]\s+\S"),
    "feature": re.compile(r"^(FEAT-\d{2})\s+[\u2014\u2013-]\s+\S"),
}
_ACCEPTED = re.compile(r"status:?\**\s*:?\s*aceit", re.IGNORECASE)
_INDEX_TITLES = {"adr": "Decisões (ADR)", "feature": "Features"}


def _tool_error(exc: ConfluenceError) -> ConfluenceToolError:
    if isinstance(exc, ConfluenceAuthError):
        return ConfluenceToolError("a conta não tem acesso a este espaço do Confluence")
    if isinstance(exc, ConfluenceNotFoundError):
        return ConfluenceToolError("página não encontrada neste espaço")
    return ConfluenceToolError("o Confluence não respondeu; tente de novo em instantes")


def _storage(markdown: str) -> tuple[str, str]:
    storage = markdown_to_storage(markdown)
    if len(storage) > MAX_STORAGE:
        raise ConfluenceToolError(
            f"a página passa de {MAX_STORAGE // 1000} mil caracteres; leve o detalhe para páginas "
            "filhas"
        )
    return storage, storage_to_markdown(storage, FULL)


def _space_out(space: DocSpace) -> dict[str, str]:
    return {"key": space.key, "name": space.name, "url": space.url}


class ConfluenceWriterAdapter:
    def __init__(
        self, client: ConfluenceClient, reader: ConfluenceReaderAdapter, project_key: str
    ) -> None:
        self._client = client
        self._space = ConfluenceSpace(
            reader.space_id, reader.space.key, reader.space.name, reader.space.url
        )
        self._reader = reader
        self._project_key = project_key
        self.space = reader.space
        self._index: list[DocPage] | None = None
        self._home: str | None = None

    async def _pages(self) -> list[DocPage]:
        if self._index is None:
            self._index = await self._reader.index()
        return self._index

    async def _homepage(self) -> str | None:
        if self._home is None:
            space = await self._client.space_by_key(self._space.key)
            self._home = (space.homepage_id if space else None) or ""
        return self._home or None

    async def _titled(self, text: str, exact: bool) -> list[str]:
        op = "=" if exact else "~"
        cql = (
            f"space = {cql_string(self._space.key)} AND type = page AND "
            f"title {op} {cql_string(text)}"
        )
        return [p.title for p in await self._client.search(cql, 5)]

    async def _parent(self, kind: str, pages: list[DocPage]) -> tuple[str | None, str]:
        if kind in _INDEX_TITLES:
            prefix = "ADR-" if kind == "adr" else "FEAT-"
            for page in pages:
                if page.kind == kind and not page.title.upper().startswith(prefix):
                    return page.id, page.title
        home = await self._homepage()
        return home, "Início" if home else ""

    async def draft_create(self, kind: str, title: str, markdown: str, summary: str) -> PageDraft:
        if kind not in WRITABLE:
            raise ConfluenceToolError(f"tipo de página inválido: {kind}")
        try:
            pages = await self._pages()
            if kind in SINGLETONS:
                for page in pages:
                    if page.kind == kind:
                        raise ConfluenceToolError(
                            f'o espaço já tem a página "{page.title}" (id {page.id}): leia com '
                            "`ler_pagina_confluence` e use `propor_atualizacao_pagina`"
                        )
            if kind in _NUMBERED:
                number = _NUMBERED[kind].match(title)
                if number is None:
                    example = "ADR-001 — <decisão>" if kind == "adr" else "FEAT-01 — <nome>"
                    raise ConfluenceToolError(f'o título deve seguir "{example}"')
                if await self._titled(number[1], exact=False):
                    raise ConfluenceToolError(
                        f"{number[1]} já existe no espaço: use o próximo número livre (IDs nunca "
                        "são reutilizados)"
                    )
            if await self._titled(title, exact=True):
                raise ConfluenceToolError(f'já existe uma página "{title}" no espaço')
            parent_id, parent_title = await self._parent(kind, pages)
        except ConfluenceError as exc:
            raise _tool_error(exc) from None
        storage, after = _storage(markdown)
        payload: dict[str, Any] = {
            "project_key": self._project_key,
            "space_id": self._space.id,
            "space_key": self._space.key,
            "parent_id": parent_id,
            "title": title,
            "storage": storage,
            "labels": labels_for(kind),
            "page_type": kind,
            "summary": summary,
        }
        preview = {
            "title": title,
            "page_type": kind,
            "summary": summary,
            "space": _space_out(self.space),
            "parent_title": parent_title,
            "diff": section_diff("", after),
        }
        return PageDraft("create_page", payload, preview)

    async def draft_update(
        self, page_id: str, markdown: str, summary: str, title: str | None
    ) -> PageDraft:
        try:
            page = await self._client.page(page_id)
            pages = await self._pages()
        except ConfluenceError as exc:
            raise _tool_error(exc) from None
        if page.space_id != self._space.id:
            raise ConfluenceToolError("a página não é do espaço vinculado a este projeto")
        indexed = {p.id: p.kind for p in pages}
        kind = indexed.get(page.id) or kind_of(page.title, ())
        if kind == "registro":
            raise ConfluenceToolError(
                "o Registro de mudanças é escrito pelo SpecFlow a cada confirmação"
            )
        if kind not in WRITABLE:
            raise ConfluenceToolError(
                "só páginas do modelo da metodologia podem ser atualizadas; as outras são só "
                "leitura"
            )
        before = storage_to_markdown(page.storage, FULL)
        if len(before) > READ_LIMIT:
            raise ConfluenceToolError(
                "a página é longa demais para ser reescrita inteira; leve o detalhe para páginas "
                "filhas ou edite no Confluence"
            )
        if kind == "adr" and page.title.upper().startswith("ADR-") and _ACCEPTED.search(before):
            raise ConfluenceToolError(
                "ADR aceita não é editada: proponha uma ADR nova que a substitui (e, nesta, só o "
                'status "Substituída por ADR-nnn")'
            )
        storage, after = _storage(markdown)
        new_title = title or page.title
        diff = section_diff(before, after)
        if not diff and new_title == page.title:
            raise ConfluenceToolError("o conteúdo proposto é igual ao da página; nada a atualizar")
        payload: dict[str, Any] = {
            "project_key": self._project_key,
            "space_id": self._space.id,
            "space_key": self._space.key,
            "page_id": page.id,
            "title": new_title,
            "storage": storage,
            "version": page.version,
            "labels": labels_for(kind),
            "page_type": kind,
            "summary": summary,
        }
        preview: dict[str, Any] = {
            "title": new_title,
            "page_type": kind,
            "summary": summary,
            "space": _space_out(self.space),
            "url": page.url,
            "version": page.version,
            "diff": diff,
        }
        if new_title != page.title:
            preview["previous_title"] = page.title
        return PageDraft("update_page", payload, preview)


def space_key_for(project_key: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", project_key).upper()[:10] or "DOCS"


class SpaceCreatorAdapter:
    def __init__(self, client: ConfluenceClient, project_key: str) -> None:
        self._client = client
        self.project_key = project_key

    async def draft_space(self, project_name: str) -> PageDraft:
        key = space_key_for(self.project_key)
        try:
            existing = await self._client.space_by_key(key)
        except ConfluenceError as exc:
            raise _tool_error(exc) from None
        if existing is not None:
            raise ConfluenceToolError(
                f'já existe o espaço "{existing.name}" com a chave {key}: o usuário pode '
                "vinculá-lo em Projects, sem criar outro"
            )
        name = f"{project_name} — Documentação"
        pages = [
            {
                "ref": page.ref,
                "parent": page.parent,
                "title": page.title,
                "kind": page.kind,
                "storage": markdown_to_storage(
                    fill(template(page.template), project_name, self.project_key)
                ),
                "labels": labels_for(page.kind)
                + (
                    [f"specflow-projeto-{self.project_key.lower()}"] if page.ref == "inicio" else []
                ),
            }
            for page in SPACE_TREE
        ]
        payload = {
            "project_key": self.project_key,
            "space_key": key,
            "space_name": name,
            "pages": pages,
        }
        preview = {
            "title": name,
            "space_key": key,
            "project_key": self.project_key,
            "pages": [p.title for p in SPACE_TREE],
        }
        return PageDraft("create_space", payload, preview)
