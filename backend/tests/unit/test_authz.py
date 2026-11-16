"""Matriz de autorização: toda rota de /api/** contra cada tipo de token (F03-RT-01, RT-02, RT-07).

As rotas vêm do esquema OpenAPI do app, então uma rota nova entra na matriz sem editar este teste.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.agent.fake_llm import EchoChatModel
from app.api.deps import (
    get_account_service,
    get_action_service,
    get_chat_service,
    get_jira_service,
    get_verifier,
)
from app.core.config import Settings, get_settings
from app.core.crypto import LocalFernetCipher
from app.main import create_app
from app.services.account import AccountService
from app.services.actions import ActionService
from app.services.chat import ChatService
from app.services.jira_connections import JiraConnectionService
from tests.chat_fakes import MemoryChatStore
from tests.fakes import FakeVerifier, MemoryJiraStore, MemoryStore

_OPENAPI = create_app().openapi()
_HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
API_ROUTES = [
    (method.upper(), path)
    for path, operations in _OPENAPI["paths"].items()
    if path.startswith("/api/")
    for method in sorted(operations)
    if method in _HTTP_METHODS
]


@pytest.fixture
def verifier() -> FakeVerifier:
    return FakeVerifier()


@pytest.fixture
def client(verifier: FakeVerifier) -> Iterator[TestClient]:
    app = create_app()
    store = MemoryStore()
    app.dependency_overrides[get_settings] = lambda: Settings(env="test")
    app.dependency_overrides[get_verifier] = lambda: verifier
    app.dependency_overrides[get_account_service] = lambda: AccountService(store)
    jira = JiraConnectionService(MemoryJiraStore(), LocalFernetCipher())
    app.dependency_overrides[get_jira_service] = lambda: jira
    chat_store = MemoryChatStore()
    chat = ChatService(chat_store, jira, EchoChatModel(), Settings(env="test"))
    app.dependency_overrides[get_chat_service] = lambda: chat
    actions = ActionService(chat_store, jira, Settings(env="test"))
    app.dependency_overrides[get_action_service] = lambda: actions
    with TestClient(app) as c:
        yield c


def _path(path: str) -> str:
    return path.replace("{", "").replace("}", "")  # parâmetros de rota viram valores literais


def test_existem_rotas_de_api_na_matriz() -> None:
    assert ("GET", "/api/v1/me") in API_ROUTES


@pytest.mark.req("F03-RF-04")
@pytest.mark.parametrize(("method", "path"), API_ROUTES)
@pytest.mark.parametrize(
    "authorization",
    [None, "", "Bearer", "Bearer   ", "Basic ok:alice", "ok:alice", "Bearer invalido"],
    ids=["sem-header", "vazio", "sem-token", "token-em-branco", "basic", "sem-esquema", "invalido"],
)
def test_rota_recusa_sem_token_valido(
    client: TestClient, method: str, path: str, authorization: str | None
) -> None:
    headers = {} if authorization is None else {"Authorization": authorization}
    response = client.request(method, _path(path), headers=headers)

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["code"] == "unauthenticated"


@pytest.mark.req("F03-RF-02")
@pytest.mark.parametrize(("method", "path"), API_ROUTES)
def test_conta_de_email_nao_verificada_recebe_403(
    client: TestClient, method: str, path: str
) -> None:
    headers = {"Authorization": "Bearer ok:unverified"}
    response = client.request(method, _path(path), headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "email-not-verified"


@pytest.mark.parametrize(("method", "path"), API_ROUTES)
def test_token_valido_passa_pela_autenticacao(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, _path(path), headers={"Authorization": "Bearer ok:alice"})

    assert response.status_code not in {401, 403}


def test_nenhuma_rota_recebe_o_usuario_por_parametro() -> None:
    # F03-RT-02: o usuário vem só do token; nenhuma rota aceita uid na rota, query ou corpo.
    suspeitos = {"uid", "user_id", "userid", "user"}
    schemas = _OPENAPI.get("components", {}).get("schemas", {})
    for method, path in API_ROUTES:
        operation = _OPENAPI["paths"][path][method.lower()]
        names = {p["name"].lower() for p in operation.get("parameters", [])}
        body = operation.get("requestBody", {}).get("content", {}).get("application/json", {})
        ref = body.get("schema", {}).get("$ref", "")
        if ref:
            names |= {n.lower() for n in schemas[ref.rsplit("/", 1)[-1]].get("properties", {})}
        assert not names & suspeitos, f"{method} {path} recebe {names & suspeitos}"


def test_uid_na_query_e_ignorado(client: TestClient) -> None:
    response = client.get("/api/v1/me?uid=uid-bob", headers={"Authorization": "Bearer ok:alice"})

    assert response.status_code == 200
    assert response.json()["uid"] == "uid-alice"


def test_exclusao_exige_token_nao_revogado(client: TestClient, verifier: FakeVerifier) -> None:
    verifier.revoked.add("ok:alice")
    headers = {"Authorization": "Bearer ok:alice"}

    assert client.get("/api/v1/me", headers=headers).status_code == 200
    assert client.delete("/api/v1/me", headers=headers).status_code == 401
    assert ("ok:alice", True) in verifier.calls
