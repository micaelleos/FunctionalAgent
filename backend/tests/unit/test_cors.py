"""CORS para o SPA hospedado (ADR-002)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app

SITE = "https://specsflow-ai.web.app"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    # Mesmos valores que o Terraform injeta no Cloud Run (infra/terraform/main.tf).
    monkeypatch.setenv("ENV", "prd")
    monkeypatch.setenv("CORS_ORIGINS", f'["{SITE}"]')
    get_settings.cache_clear()
    with TestClient(create_app()) as c:
        yield c
    get_settings.cache_clear()


def _allowed_origin(client: TestClient, origin: str) -> str | None:
    headers = client.get("/healthz", headers={"Origin": origin}).headers
    value: str | None = headers.get("access-control-allow-origin")
    return value


def test_aceita_o_site_principal(client: TestClient) -> None:
    assert _allowed_origin(client, SITE) == SITE


@pytest.mark.parametrize(
    "origin",
    [
        "https://specsflow-ai--pr-12-a1b2c3d4.web.app",  # canal de preview (não usamos)
        "https://pcb-inspect--pr-1.web.app",  # outro app do portfólio
        "https://pcb-inspect.web.app",
        "https://evil.web.app",
        "https://specsflow-ai--pr-1.web.app.evil.com",
        "http://specsflow-ai--pr-1.web.app",
    ],
)
def test_recusa_outras_origens(client: TestClient, origin: str) -> None:
    assert _allowed_origin(client, origin) is None
