"""Documentos do Confluence escritos pelo SpecFlow: `/api/v1/documents` (F20-RF-08)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, Documents
from app.services.documents import DocumentOut

router = APIRouter(prefix="/api/v1/documents", tags=["confluence"])


@router.get("", summary="Páginas do Confluence criadas ou atualizadas pelo SpecFlow")
async def list_documents(
    user: CurrentUser,
    service: Documents,
    project: Annotated[str | None, Query(max_length=20, pattern=r"^[A-Z][A-Z0-9_]{1,9}$")] = None,
) -> list[DocumentOut]:
    return await service.list(user.uid, project)
