"""Erros do SPA → Error Reporting (F11-RT-11)."""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.logging import JsonFormatter
from app.main import create_app

pytestmark = pytest.mark.req("F11-RT-11")

URL = "/api/v1/client-errors"


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(env="test")
    return TestClient(app)


def test_relato_vira_log_do_error_reporting(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR, logger="app.client")
    with _client() as client:
        response = client.post(
            URL,
            json={
                "message": "TypeError: x is undefined",
                "stack": "TypeError: x is undefined\n    at ChatPage (index.js:1:2)",
                "url": "https://specsflow-ai.web.app/chat/abc?projeto=SCRUM#fim",
                "release": "d561fd8dc788",
                "kind": "render",
            },
        )

    assert response.status_code == 204
    [record] = caplog.records
    line = json.loads(JsonFormatter("pcb-inspect").format(record))
    assert line["severity"] == "ERROR"
    assert line["@type"].endswith("ReportedErrorEvent")
    assert line["serviceContext"] == {"service": "specflow-web", "version": "d561fd8dc788"}
    assert line["context"]["httpRequest"]["url"] == "/chat/abc"  # sem query nem fragmento
    assert line["message"].startswith("TypeError: x is undefined\nTypeError")


def test_corpo_grande_ou_invalido_e_recusado() -> None:
    with _client() as client:
        big = client.post(URL, json={"message": "x" * 501})
        kind = client.post(URL, json={"message": "x", "kind": "outro"})
        huge = client.post(
            URL,
            content=json.dumps({"message": "x", "stack": "y" * 9000}),
            headers={"Content-Type": "application/json"},
        )

    assert (big.status_code, kind.status_code) == (422, 422)
    assert huge.status_code in {413, 422}
