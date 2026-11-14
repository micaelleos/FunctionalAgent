"""Erros em Problem Details (F03-RT-05)."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import ApiProblemError, install_problem_handlers


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = FastAPI()
    install_problem_handlers(app)

    @app.get("/conflito")
    def conflito() -> None:
        raise ApiProblemError(409, "conflict", "Conflito", "Já existe", resource="x")

    @app.get("/numero/{n}")
    def numero(n: int) -> int:
        return n

    with TestClient(app) as c:
        yield c


def test_erro_de_dominio_vira_problem_details(client: TestClient) -> None:
    response = client.get("/conflito")

    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "https://specsflow-ai.web.app/problemas/conflict",
        "title": "Conflito",
        "status": 409,
        "code": "conflict",
        "detail": "Já existe",
        "instance": "/conflito",
        "resource": "x",
    }


def test_rota_inexistente_vira_problem_details(client: TestClient) -> None:
    response = client.get("/nao-existe")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Não encontrado"


def test_erro_de_validacao_vira_problem_details(client: TestClient) -> None:
    response = client.get("/numero/abc")

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation-error"
    assert body["errors"][0]["loc"] == ["path", "n"]
