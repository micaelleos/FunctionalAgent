"""Páginas do Confluence escritas pelo SpecFlow, para a aba "Docs" (F20-RF-08, F20-RT-07)."""

from datetime import datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel

from app.core.telemetry import in_thread


class DocumentStore(Protocol):
    def list_documents(self, uid: str, project_key: str | None = None) -> list[dict[str, Any]]: ...


class DocumentOut(BaseModel):
    page_id: str
    project_key: str | None
    space_key: str | None
    type: str
    title: str
    url: str
    version: int
    operation: Literal["created", "updated"]
    created_at: datetime
    updated_at: datetime


def _out(doc: dict[str, Any]) -> DocumentOut:
    return DocumentOut(
        page_id=str(doc["pageId"]),
        project_key=doc.get("projectKey"),
        space_key=doc.get("spaceKey"),
        type=str(doc.get("type") or ""),
        title=str(doc.get("title") or ""),
        url=str(doc.get("url") or ""),
        version=int(doc.get("version") or 0),
        operation="updated" if doc.get("operation") == "updated" else "created",
        created_at=doc.get("createdAt") or doc["updatedAt"],
        updated_at=doc["updatedAt"],
    )


class DocumentService:
    def __init__(self, store: DocumentStore) -> None:
        self._store = store

    async def list(self, uid: str, project_key: str | None = None) -> list[DocumentOut]:
        docs = await in_thread(self._store.list_documents, uid, project_key)
        return [_out(d) for d in docs]
