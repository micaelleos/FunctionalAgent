"""Logs estruturados no formato do Cloud Logging (F11-RT-01).

Cada linha é um JSON com `severity`, `message`, o trace da requisição e `request_id`/`uid_hash`. O
`uid` nunca vai para o log (Art. II): só um hash curto, suficiente para correlacionar eventos de um
usuário. Conteúdo de mensagens e segredos também não: os eventos levam só contagens e códigos.
"""

import hashlib
import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Um dict mutável por requisição: dependências síncronas do FastAPI rodam numa cópia do contexto
# (threadpool), então atribuir um ContextVar ali se perderia; mutar o dict compartilhado não.
_request: ContextVar[dict[str, str] | None] = ContextVar("specflow_request", default=None)

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_CLOUD_TRACE = re.compile(r"^([0-9a-f]{32})(?:/(\d+))?")
_TRACEPARENT = re.compile(r"^[0-9a-f]{2}-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}$")

APP_LOGGER = "app"


def uid_hash(uid: str) -> str:
    return hashlib.sha256(uid.encode()).hexdigest()[:16]


def bind(**fields: str) -> None:
    """Acrescenta campos ao contexto da requisição atual (ex.: `uid_hash` depois do login)."""
    ctx = _request.get()
    if ctx is not None:
        ctx.update(fields)


def current() -> dict[str, str]:
    return dict(_request.get() or {})


def parse_trace(headers: dict[str, str]) -> dict[str, str]:
    """Trace do Cloud Run (`X-Cloud-Trace-Context`) ou W3C (`traceparent`)."""
    if match := _TRACEPARENT.match(headers.get("traceparent", "")):
        return {"trace_id": match.group(1), "span_id": match.group(2)}
    if match := _CLOUD_TRACE.match(headers.get("x-cloud-trace-context", "")):
        found = {"trace_id": match.group(1)}
        if match.group(2):
            found["span_id"] = f"{int(match.group(2)):016x}"
        return found
    return {}


class JsonFormatter(logging.Formatter):
    def __init__(self, project: str | None) -> None:
        super().__init__()
        self._project = project

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.exc_info:
            # Com o traceback na mensagem, o Error Reporting agrupa o erro sozinho.
            message = f"{message}\n{self.formatException(record.exc_info)}"
        payload: dict[str, Any] = {
            "severity": "CRITICAL" if record.levelno >= logging.CRITICAL else record.levelname,
            "message": message,
            "logger": record.name,
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
        }
        ctx = _request.get() or {}
        for key in ("request_id", "uid_hash"):
            if key in ctx:
                payload[key] = ctx[key]
        trace_id, span_id = _active_span() or (ctx.get("trace_id"), ctx.get("span_id"))
        if trace_id and self._project:
            payload["logging.googleapis.com/trace"] = f"projects/{self._project}/traces/{trace_id}"
            if span_id:
                payload["logging.googleapis.com/spanId"] = span_id
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        return json.dumps(payload, ensure_ascii=False, default=str)


def _active_span() -> tuple[str, str] | None:
    """Trace/span do OpenTelemetry, quando o tracing está ligado (F11-RT-02)."""
    try:
        from opentelemetry import trace
    except ImportError:  # pragma: no cover - a dependência faz parte da imagem
        return None
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return None
    return f"{context.trace_id:032x}", f"{context.span_id:016x}"


def configure_logging(project: str | None, level: int = logging.INFO) -> None:
    """Loggers `app.*` em JSON no stdout, nível INFO. Idempotente (testes criam vários apps).

    Continua propagando para o raiz, que não tem handler em produção (o uvicorn só configura os
    loggers dele), para o `caplog` dos testes enxergar os eventos."""
    logger = logging.getLogger(APP_LOGGER)
    logger.setLevel(level)
    for handler in list(logger.handlers):
        if getattr(handler, "_specflow", False):
            logger.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(project))
    handler._specflow = True  # type: ignore[attr-defined]
    logger.addHandler(handler)


class RequestContextMiddleware:
    """ASGI puro (não quebra o streaming SSE): `request_id` e trace no contexto e no header."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        given = headers.get("x-request-id", "")
        request_id = given if _REQUEST_ID.match(given) else uuid.uuid4().hex
        token = _request.set({"request_id": request_id, **parse_trace(headers)})

        async def with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                message["headers"] = [*message["headers"], (b"x-request-id", request_id.encode())]
            await send(message)

        try:
            await self.app(scope, receive, with_header)
        finally:
            _request.reset(token)
