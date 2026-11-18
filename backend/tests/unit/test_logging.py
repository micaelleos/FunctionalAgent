"""Logs estruturados e traces (F11-RT-01, F11-RT-02)."""

import json
import logging
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind

from app.agent.fake_llm import ScriptedChatModel
from app.api.deps import get_verifier
from app.core.config import Settings, get_settings
from app.core.logging import JsonFormatter, configure_logging, parse_trace, uid_hash
from app.main import create_app
from tests.fakes import FakeVerifier
from tests.unit.test_chat_service import _service, _turn

pytestmark = pytest.mark.req("F11-RT-01")

TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"
SECRET_TEXT = "texto-secreto-do-usuario-123"

# Um provider em memória para o processo de testes (o global só pode ser definido uma vez).
SPANS = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(SPANS))
trace.set_tracer_provider(_provider)


def _format(record: logging.LogRecord, project: str | None = "pcb-inspect") -> dict[str, Any]:
    return dict(json.loads(JsonFormatter(project).format(record)))


def _record(msg: str = "evento", level: int = logging.INFO, **extra: Any) -> logging.LogRecord:
    record = logging.LogRecord("app.teste", level, __file__, 1, msg, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_linha_json_com_severidade_e_campos() -> None:
    line = _format(_record(fields={"event": "chat_turn", "input_tokens": 3}))

    assert line["severity"] == "INFO"
    assert line["message"] == "evento"
    assert (line["event"], line["input_tokens"]) == ("chat_turn", 3)
    assert "uid" not in line


def test_excecao_vai_na_mensagem_para_o_error_reporting() -> None:
    try:
        raise RuntimeError("quebrou")
    except RuntimeError:
        record = _record("falhou", logging.ERROR, exc_info=sys.exc_info())

    line = _format(record)

    assert line["severity"] == "ERROR"
    assert line["message"].startswith("falhou\nTraceback")
    assert "RuntimeError: quebrou" in line["message"]


def test_trace_do_cloud_run_e_do_w3c() -> None:
    assert parse_trace({"x-cloud-trace-context": f"{TRACE}/1;o=1"}) == {
        "trace_id": TRACE,
        "span_id": "0000000000000001",
    }
    assert parse_trace({"traceparent": f"00-{TRACE}-00f067aa0ba902b7-01"}) == {
        "trace_id": TRACE,
        "span_id": "00f067aa0ba902b7",
    }
    assert parse_trace({"x-cloud-trace-context": "lixo"}) == {}


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(env="test")
    app.dependency_overrides[get_verifier] = FakeVerifier
    return TestClient(app)


def test_requisicao_ganha_request_id_trace_e_uid_hash(
    caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("pcb-inspect")
    with _client() as client:
        given = client.get("/api/v1/me", headers={"X-Request-Id": "req-123"})
        generated = client.get("/health")
        bad = client.get("/health", headers={"X-Request-Id": "com espaco"})

    assert given.headers["x-request-id"] == "req-123"
    assert len(generated.headers["x-request-id"]) == 32
    assert bad.headers["x-request-id"] != "com espaco"

    # Um log dentro da requisição carrega o contexto (sem o uid).
    seen: list[dict[str, Any]] = []

    class Grab(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            seen.append(json.loads(JsonFormatter("pcb-inspect").format(record)))

    logger = logging.getLogger("app.teste")
    handler = Grab()
    logger.addHandler(handler)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(env="test")
    app.dependency_overrides[get_verifier] = FakeVerifier

    from app.api.deps import CurrentUser

    @app.get("/teste-log-user")
    def teste_log_user(user: CurrentUser) -> dict[str, str]:
        logger.info("dentro")
        return {}

    try:
        with TestClient(app) as client:
            client.get(
                "/teste-log-user",
                headers={
                    "Authorization": "Bearer ok:alice",
                    "X-Request-Id": "req-9",
                    # Propagador W3C nos testes; em prd é o do GCP (X-Cloud-Trace-Context).
                    "traceparent": f"00-{TRACE}-00f067aa0ba902b7-01",
                },
            )
    finally:
        logger.removeHandler(handler)

    [line] = seen
    assert line["request_id"] == "req-9"
    assert line["uid_hash"] == uid_hash("uid-alice")
    assert line["logging.googleapis.com/trace"] == f"projects/pcb-inspect/traces/{TRACE}"
    assert "uid-alice" not in json.dumps(line)


async def test_chat_turn_sem_uid_e_sem_conteudo(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="app.chat")
    service, _, _ = _service(ScriptedChatModel(responses=[AIMessage(f"Resposta {SECRET_TEXT}")]))

    await _turn(service, f"Pergunta {SECRET_TEXT}")

    [record] = [r for r in caplog.records if getattr(r, "fields", {}).get("event") == "chat_turn"]
    line = _format(record)
    assert line["uid_hash"] == uid_hash("uid-alice")
    assert isinstance(line["first_token_ms"], int)
    assert line["duration_ms"] >= line["first_token_ms"]
    assert SECRET_TEXT not in json.dumps(line)
    assert "uid-alice" not in json.dumps(line)


@pytest.mark.req("F11-RT-02")
def test_span_da_requisicao_continua_o_trace_do_cloud_run() -> None:
    SPANS.clear()
    with _client() as client:
        client.get(
            "/health",
            headers={"traceparent": f"00-{TRACE}-00f067aa0ba902b7-01"},
        )

    [server] = [s for s in SPANS.get_finished_spans() if s.kind == SpanKind.SERVER]
    assert f"{server.context.trace_id:032x}" == TRACE
    assert server.parent is not None


@pytest.mark.req("F11-RT-02")
async def test_chamadas_ao_firestore_viram_spans() -> None:
    SPANS.clear()
    service, _, _ = _service(ScriptedChatModel(responses=[AIMessage("Oi")]))

    await _turn(service, "Olá")

    names = {s.name for s in SPANS.get_finished_spans()}
    assert {"store.create_conversation", "store.add_message"} <= names
