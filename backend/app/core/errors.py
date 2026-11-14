"""Erros da API no formato Problem Details, RFC 9457 (F03-RT-05)."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_JSON = "application/problem+json"
_TYPE_BASE = "https://specsflow-ai.web.app/problemas/"


class ApiProblemError(Exception):
    """Erro de domínio que vira uma resposta Problem Details.

    `code` é estável e o front usa para escolher a mensagem (ex.: `email-not-verified`).
    """

    def __init__(
        self, status: int, code: str, title: str, detail: str | None = None, **extra: Any
    ) -> None:
        super().__init__(title)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.extra = extra
        self.headers: dict[str, str] = {}


class UnauthenticatedError(ApiProblemError):
    def __init__(self, detail: str = "Faça login para continuar.") -> None:
        super().__init__(401, "unauthenticated", "Não autenticado", detail)
        self.headers = {"WWW-Authenticate": "Bearer"}


class EmailNotVerifiedError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(
            403,
            "email-not-verified",
            "E-mail não verificado",
            "Confirme seu e-mail pelo link que enviamos e entre de novo.",
        )


def problem_response(
    status: int,
    code: str,
    title: str,
    detail: str | None = None,
    instance: str | None = None,
    headers: dict[str, str] | None = None,
    **extra: Any,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": _TYPE_BASE + code,
        "title": title,
        "status": status,
        "code": code,
    }
    if detail:
        body["detail"] = detail
    if instance:
        body["instance"] = instance
    body.update(extra)
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON, headers=headers)


_TITLES = {404: "Não encontrado", 405: "Método não permitido", 500: "Erro interno"}


def install_problem_handlers(app: FastAPI) -> None:
    async def on_problem(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, ApiProblemError)  # noqa: S101 - garantido pelo registro do handler
        return problem_response(
            exc.status,
            exc.code,
            exc.title,
            exc.detail,
            instance=request.url.path,
            headers=exc.headers or None,
            **exc.extra,
        )

    async def on_http(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, StarletteHTTPException)  # noqa: S101
        title = _TITLES.get(exc.status_code, "Erro")
        detail = exc.detail if isinstance(exc.detail, str) and exc.detail != title else None
        return problem_response(
            exc.status_code,
            f"http-{exc.status_code}",
            title,
            detail,
            instance=request.url.path,
            headers=getattr(exc, "headers", None),
        )

    async def on_validation(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, RequestValidationError)  # noqa: S101
        errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        return problem_response(
            422,
            "validation-error",
            "Dados inválidos",
            instance=request.url.path,
            errors=errors,
        )

    app.add_exception_handler(ApiProblemError, on_problem)
    app.add_exception_handler(StarletteHTTPException, on_http)
    app.add_exception_handler(RequestValidationError, on_validation)
