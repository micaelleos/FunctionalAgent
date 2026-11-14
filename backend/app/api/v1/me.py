"""Conta do usuário autenticado: `/api/v1/me` (F03)."""

from typing import Any

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse

from app.api.deps import Account, CurrentUser, CurrentUserChecked
from app.services.account import Profile

router = APIRouter(prefix="/api/v1/me", tags=["conta"])


@router.get("", response_model=Profile, summary="Perfil (criado no primeiro acesso)")
def get_me(user: CurrentUser, account: Account) -> Profile:
    return account.profile(user)


@router.get("/export", summary="Baixa todos os meus dados (JSON)")
def export_me(user: CurrentUser, account: Account) -> JSONResponse:
    data: dict[str, Any] = account.export(user)
    return JSONResponse(
        data,
        headers={"Content-Disposition": 'attachment; filename="specflow-meus-dados.json"'},
    )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui meus dados do SpecFlow AI (o login do portfólio continua)",
)
def delete_me(user: CurrentUserChecked, account: Account) -> Response:
    account.delete(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
