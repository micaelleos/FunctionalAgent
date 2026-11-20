"""Execução das ações do Confluence na confirmação (F20-RF-01, F20-RF-04, F20-RF-07, F20-RT-01).

Chamada só pela confirmação da F06 (`ActionService`), depois do hash conferido: escreve exatamente o
payload exibido. Atualização vai com a versão vista na proposta; se a página mudou, o Confluence
recusa (409) e nada é sobrescrito. Sem DELETE: uma criação de espaço que falha no meio deixa o que
foi criado e diz o que falta. O "Registro de mudanças" ganha uma linha na mesma confirmação; se ele
falhar, a escrita principal vale e o resultado traz um aviso.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from typing import Any, Protocol

from app.core.telemetry import in_thread
from app.integrations.confluence.client import (
    ConfluenceAuthError,
    ConfluenceBadRequestError,
    ConfluenceClient,
    ConfluenceConflictError,
    ConfluenceError,
    ConfluenceNotFoundError,
    ConfluencePage,
    ConfluenceRateLimitedError,
    ConfluenceSpace,
    ConfluenceUnreachableError,
    cql_string,
)

log = logging.getLogger("app.confluence")

DOC_KINDS = ("create_page", "update_page", "create_space")
REGISTRY_WARNING = "A página foi escrita, mas o Registro de mudanças não foi atualizado."
VERSION_CONFLICT = (
    "A página mudou no Confluence depois da proposta e não foi sobrescrita. Peça ao agente para "
    "revisar de novo."
)


class LinkStore(Protocol):
    def set(self, uid: str, project_key: str, data: dict[str, Any]) -> None: ...


class DocsWriteError(Exception):
    def __init__(self, code: str, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass
class DocsOutcome:
    page_id: str
    title: str
    url: str
    documents: dict[str, dict[str, Any]] = field(default_factory=dict)
    warning: str | None = None


def describe_doc(doc: dict[str, Any]) -> str:
    payload = doc.get("payload") or {}
    if doc["kind"] == "create_space":
        return f'criar o espaço "{payload.get("space_name")}" no Confluence'
    verb = "criar" if doc["kind"] == "create_page" else "atualizar"
    return f'{verb} a página "{payload.get("title")}" no Confluence'


def translate(kind: str, payload: dict[str, Any], exc: ConfluenceError) -> DocsWriteError:
    """Erro do Confluence → código e mensagem em pt-BR (o cartão traduz pelo código)."""
    if isinstance(exc, ConfluenceConflictError):
        if kind == "update_page":
            return DocsWriteError("confluence-version-conflict", VERSION_CONFLICT, False)
        if kind == "create_space":
            return DocsWriteError(
                "confluence-space-key-taken",
                f"Já existe um espaço com a chave {payload.get('space_key')}.",
                False,
            )
        return DocsWriteError(
            "confluence-rejected", f'Já existe uma página "{payload.get("title")}".', False
        )
    if isinstance(exc, ConfluenceAuthError):
        return DocsWriteError(
            "confluence-forbidden",
            "Sua conta Atlassian não tem permissão para escrever neste espaço do Confluence.",
            False,
        )
    if isinstance(exc, ConfluenceNotFoundError):
        return DocsWriteError(
            "confluence-not-found",
            "A página ou o espaço não existe mais no Confluence (ou você perdeu o acesso).",
            False,
        )
    if isinstance(exc, ConfluenceBadRequestError):
        if kind == "create_space" and "key" in str(exc).lower():
            return DocsWriteError(
                "confluence-space-key-taken",
                f"O Confluence recusou a chave {payload.get('space_key')}: {exc}",
                False,
            )
        return DocsWriteError("confluence-rejected", f"O Confluence recusou: {exc}", False)
    if isinstance(exc, ConfluenceRateLimitedError):
        return DocsWriteError(
            "confluence-rate-limited",
            "O Confluence está limitando as requisições. Confirme de novo em alguns minutos.",
            True,
        )
    if isinstance(exc, ConfluenceUnreachableError):
        return DocsWriteError(
            "confluence-unreachable",
            "Não foi possível falar com o Confluence agora. Confirme de novo em instantes.",
            True,
        )
    return DocsWriteError(
        "confluence-uncertain",
        "O Confluence não respondeu a tempo. Confira no Confluence se a página foi escrita antes "
        "de pedir de novo.",
        False,
    )


def append_row(storage: str, cells: list[str]) -> str:
    """Linha nova na tabela do Registro (células já em XHTML); sem tabela, cria uma."""
    row = "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
    end = storage.rfind("</tbody>")
    if end >= 0:
        return storage[:end] + row + storage[end:]
    header = "".join(f"<th>{h}</th>" for h in ("Data", "Página", "Resumo", "Autor"))
    return f"{storage}<table><tbody><tr>{header}</tr>{row}</tbody></table>"


class ConfluenceActionExecutor:
    def __init__(self, links: LinkStore, clock: Callable[[], datetime]) -> None:
        self._links = links
        self._clock = clock

    async def execute(
        self,
        uid: str,
        doc: dict[str, Any],
        client: ConfluenceClient,
        connection_id: str,
        confirmed_by: str,
    ) -> DocsOutcome:
        kind, payload = doc["kind"], doc["payload"]
        if kind == "create_space":
            return await self._space(uid, doc, client, connection_id, confirmed_by)
        try:
            if kind == "create_page":
                page = await client.create_page(
                    str(payload["space_id"]),
                    str(payload["title"]),
                    str(payload["storage"]),
                    payload.get("parent_id"),
                )
            else:
                page = await client.update_page(
                    str(payload["page_id"]),
                    str(payload["title"]),
                    str(payload["storage"]),
                    int(payload["version"]),
                    f"SpecFlow: {payload.get('summary', '')}",
                )
        except ConfluenceError as exc:
            raise translate(kind, payload, exc) from None
        warnings: list[str] = []
        try:
            await client.add_labels(page.id, list(payload.get("labels") or []))
        except ConfluenceError:
            warnings.append("Os rótulos da página não foram gravados.")
        operation = "created" if kind == "create_page" else "updated"
        outcome = DocsOutcome(
            page.id,
            page.title or str(payload["title"]),
            page.url,
            {page.id: self._record(doc, page, str(payload.get("page_type", "")), operation)},
        )
        if not await self._registry(client, payload, page, outcome.title, confirmed_by):
            warnings.append(REGISTRY_WARNING)
        outcome.warning = " ".join(warnings) or None
        return outcome

    def _record(
        self, doc: dict[str, Any], page: ConfluencePage, page_type: str, operation: str
    ) -> dict[str, Any]:
        payload, now = doc["payload"], self._clock()
        return {
            "projectKey": payload.get("project_key"),
            "spaceId": page.space_id or payload.get("space_id"),
            "spaceKey": payload.get("space_key"),
            "type": page_type,
            "title": page.title or payload.get("title"),
            "url": page.url,
            "version": page.version,
            "operation": operation,
            "lastActionId": doc["id"],
            "conversationId": doc.get("conversationId"),
            "createdAt": now,
            "updatedAt": now,
        }

    async def _registry(
        self,
        client: ConfluenceClient,
        payload: dict[str, Any],
        page: ConfluencePage,
        title: str,
        confirmed_by: str,
        registry_id: str | None = None,
    ) -> bool:
        """Linha no Registro de mudanças (F20-RF-07), com a versão lida agora."""
        try:
            if registry_id is None:
                cql = (
                    f"space = {cql_string(str(payload['space_key']))} AND type = page AND "
                    '(label = "specflow-tipo-registro" OR title = "Registro de mudanças")'
                )
                found = await client.search(cql, 1)
                if not found:
                    return False
                registry_id = found[0].id
            registry = await client.page(registry_id)
            link = f'<a href="{escape(page.url, quote=True)}">{escape(title)}</a>'
            cells = [
                self._clock().strftime("%Y-%m-%d"),
                link,
                escape(str(payload.get("summary") or "Criação do espaço com o modelo")),
                escape(f"SpecFlow, confirmado por {confirmed_by}"),
            ]
            await client.update_page(
                registry.id,
                registry.title,
                append_row(registry.storage, cells),
                registry.version,
                "SpecFlow: registro",
            )
        except ConfluenceError:
            return False
        return True

    async def _space(
        self,
        uid: str,
        doc: dict[str, Any],
        client: ConfluenceClient,
        connection_id: str,
        confirmed_by: str,
    ) -> DocsOutcome:
        payload = doc["payload"]
        try:
            space = await client.create_space(str(payload["space_key"]), str(payload["space_name"]))
        except ConfluenceError as exc:
            raise translate("create_space", payload, exc) from None
        # O espaço existe: vincula já, para a próxima conversa achar o que foi criado.
        await self._link(uid, payload, space, connection_id)
        ids: dict[str, str] = {}
        created: list[ConfluencePage] = []
        types: dict[str, str] = {}
        pending = list(payload["pages"])
        try:
            for item in pending:
                parent = ids.get(item["parent"]) if item["parent"] else None
                if item["ref"] == "inicio" and space.homepage_id:
                    home = await client.page(space.homepage_id)
                    page = await client.update_page(
                        home.id, item["title"], item["storage"], home.version, "SpecFlow: modelo"
                    )
                else:
                    page = await client.create_page(
                        space.id, item["title"], item["storage"], parent or space.homepage_id
                    )
                ids[item["ref"]] = page.id
                created.append(page)
                types[page.id] = item["kind"]
                try:
                    await client.add_labels(page.id, list(item["labels"]))
                except ConfluenceError:
                    log.warning("confluence_labels_failed")
        except ConfluenceError:
            done = ", ".join(p.title for p in created) or "nenhuma página"
            missing = ", ".join(i["title"] for i in pending[len(created) :])
            raise DocsWriteError(
                "confluence-partial",
                f"O espaço {space.key} foi criado e vinculado ({space.url}), mas a criação parou. "
                f"Criadas: {done}. Faltam: {missing}. Peça ao agente para completar o que falta.",
                False,
            ) from None
        documents = {
            p.id: {
                **self._record(doc, p, types[p.id], "created"),
                "spaceId": space.id,
                "spaceKey": space.key,
            }
            for p in created
        }
        home = created[0]
        warning = None
        registry_id = ids.get("registro")
        if not await self._registry(
            client, {**payload, "space_key": space.key}, home, space.name, confirmed_by, registry_id
        ):
            warning = "O espaço foi criado, mas o Registro de mudanças não foi atualizado."
        return DocsOutcome(home.id, space.name, space.url, documents, warning)

    async def _link(
        self, uid: str, payload: dict[str, Any], space: ConfluenceSpace, connection_id: str
    ) -> None:
        link = {
            "connectionId": connection_id,
            "spaceId": space.id,
            "spaceKey": space.key,
            "spaceName": space.name,
            "spaceUrl": space.url,
            "source": "manual",
            "linkedAt": self._clock(),
        }
        await in_thread(self._links.set, uid, str(payload["project_key"]), link)
