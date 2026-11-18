"""Erros do SPA → Error Reporting: `POST /api/v1/client-errors` (F11-RT-11, vindo da F08-RT-07).

Sem login obrigatório (o erro pode ser na tela de login). Corpo pequeno e campos truncados; a URL
vai sem query nem fragmento. Nada do que o usuário digitou entra: o SPA manda só mensagem de erro,
pilha e a rota.
"""

import logging
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, StringConstraints

from app.core.errors import ApiProblemError

router = APIRouter(prefix="/api/v1/client-errors", tags=["observabilidade"])
log = logging.getLogger("app.client")

MAX_BODY = 8 * 1024
# Formato que o Error Reporting reconhece sem traceback do Python.
REPORTED_ERROR = (
    "type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent"
)

Short = Annotated[str, StringConstraints(max_length=500)]
Long = Annotated[str, StringConstraints(max_length=6000)]


class ClientError(BaseModel):
    message: Short
    stack: Long = ""
    url: Short = ""
    release: Annotated[str, StringConstraints(max_length=64)] = ""
    kind: Annotated[str, StringConstraints(pattern=r"^(error|unhandledrejection|render)$")] = (
        "error"
    )


class PayloadTooLargeError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(413, "payload-too-large", "Relato de erro grande demais")


def _route(url: str) -> str:
    parts = urlsplit(url)
    return parts.path[:200] if parts.scheme in {"http", "https"} else ""


@router.post("", status_code=status.HTTP_204_NO_CONTENT, summary="Relata um erro do SPA")
async def report_client_error(body: ClientError, request: Request) -> Response:
    if int(request.headers.get("content-length") or 0) > MAX_BODY:
        raise PayloadTooLargeError()
    stack = body.stack if body.stack.startswith(("Error", body.message[:20])) else ""
    message = f"{body.message}\n{stack}".strip() if stack else body.message
    log.error(
        message,
        extra={
            "fields": {
                "event": "client_error",
                "kind": body.kind,
                "@type": REPORTED_ERROR,
                "serviceContext": {"service": "specflow-web", "version": body.release or "?"},
                "context": {"httpRequest": {"url": _route(body.url)}},
            }
        },
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
