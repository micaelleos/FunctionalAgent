from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(env="test", app_version="abc123")
    with TestClient(app) as c:
        yield c


@pytest.mark.req("F01-RF-02")
def test_healthz_retorna_ok_e_versao(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "abc123", "env": "test"}


@pytest.mark.req("F01-RF-02")
def test_health_publico_responde_igual_ao_healthz(client: TestClient) -> None:
    # Na URL *.run.app o Google devolve 404 para caminhos terminados em "z"; clientes usam /health.
    assert client.get("/health").json() == client.get("/healthz").json()


@pytest.mark.req("F01-RF-02")
def test_cors_permite_origem_do_frontend_local(client: TestClient) -> None:
    response = client.get("/healthz", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_docs_desabilitado_fora_de_local_e_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ENV", "prd")
    try:
        with TestClient(create_app()) as c:
            assert c.get("/docs").status_code == 404
    finally:
        get_settings.cache_clear()
