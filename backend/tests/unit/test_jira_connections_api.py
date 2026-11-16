"""Rotas /api/v1/jira/connections com Jira simulado (AT-F04-01..05 no backend)."""

import logging
from collections.abc import Iterator

import pytest
import respx
from fastapi.testclient import TestClient

from app.api.deps import get_jira_service, get_verifier
from app.core.config import Settings, get_settings
from app.core.crypto import LocalFernetCipher
from app.main import create_app
from app.services.jira_connections import JiraConnectionService
from tests.fakes import FakeVerifier, MemoryJiraStore
from tests.jira_fake import EMAIL, SITE, TOKEN, myself

ALICE = {"Authorization": "Bearer ok:alice"}
BOB = {"Authorization": "Bearer ok:bob"}
BODY = {"site_url": SITE + "/jira/software", "email": EMAIL, "api_token": TOKEN}
BASE = "/api/v1/jira/connections"


@pytest.fixture
def store() -> MemoryJiraStore:
    return MemoryJiraStore()


@pytest.fixture
def jira() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False) as router:
        myself(router)
        yield router


@pytest.fixture
def client(store: MemoryJiraStore, jira: respx.MockRouter) -> Iterator[TestClient]:
    app = create_app()
    service = JiraConnectionService(store, LocalFernetCipher())
    app.dependency_overrides[get_settings] = lambda: Settings(env="test")
    app.dependency_overrides[get_verifier] = FakeVerifier
    app.dependency_overrides[get_jira_service] = lambda: service
    with TestClient(app) as c:
        yield c


def _connect(client: TestClient, headers: dict[str, str] = ALICE) -> dict[str, str]:
    response = client.post(BASE, json=BODY, headers=headers)
    assert response.status_code == 201, response.text
    data: dict[str, str] = response.json()
    return data


@pytest.mark.req("F04-RF-01")
@pytest.mark.req("F04-RF-02")
@pytest.mark.req("F04-RF-04")
@pytest.mark.req("F04-RT-01")
@pytest.mark.req("F04-RT-02")
def test_conectar_valida_e_guarda_cifrado(client: TestClient, store: MemoryJiraStore) -> None:
    created = _connect(client)

    assert created["site_url"] == SITE
    assert created["account_name"] == "PO Teste"
    assert created["token_hint"] == TOKEN[-4:]
    assert created["status"] == "ok"
    listed = client.get(BASE, headers=ALICE)
    assert listed.json() == [created]
    for response in (listed,):
        assert TOKEN not in response.text
    doc = store.docs["uid-alice"][created["id"]]
    assert TOKEN.encode() not in doc["tokenCiphertext"]
    assert TOKEN not in str({k: v for k, v in doc.items() if k != "tokenCiphertext"})
    assert LocalFernetCipher().decrypt(doc["tokenCiphertext"]) == TOKEN
    assert doc["authType"] == "api_token"


@pytest.mark.req("F04-RF-03")
def test_credencial_recusada_nao_salva(client: TestClient, store: MemoryJiraStore) -> None:
    response = client.post(BASE, json={**BODY, "api_token": "token-errado-0000"}, headers=ALICE)

    assert response.status_code == 422
    assert response.json()["code"] == "jira-invalid-credentials"
    assert response.json()["detail"] == "O Jira recusou a credencial. Verifique e-mail e token."
    assert store.docs == {}


@pytest.mark.req("F04-RF-03")
@pytest.mark.req("F04-RT-03")
def test_url_fora_do_padrao(
    client: TestClient, jira: respx.MockRouter, store: MemoryJiraStore
) -> None:
    response = client.post(BASE, json={**BODY, "site_url": "http://169.254.169.254"}, headers=ALICE)

    assert response.status_code == 422
    assert response.json()["code"] == "jira-invalid-url"
    assert response.json()["detail"] == "Informe uma URL https://<seu-site>.atlassian.net"
    assert store.docs == {}
    assert not any("169.254" in str(c.request.url) for c in jira.calls)


@pytest.mark.req("F04-RF-03")
def test_site_inacessivel(client: TestClient, jira: respx.MockRouter) -> None:
    jira.get("https://fora-do-ar.atlassian.net/rest/api/3/myself").respond(404)
    body = {**BODY, "site_url": "https://fora-do-ar.atlassian.net"}

    response = client.post(BASE, json=body, headers=ALICE)

    assert response.status_code == 502
    assert response.json()["code"] == "jira-unreachable"


def test_uma_conexao_por_usuario(client: TestClient) -> None:
    _connect(client)

    response = client.post(BASE, json=BODY, headers=ALICE)

    assert response.status_code == 409
    assert response.json()["code"] == "jira-connection-exists"


@pytest.mark.req("F04-RF-05")
def test_trocar_credencial(
    client: TestClient, jira: respx.MockRouter, store: MemoryJiraStore
) -> None:
    created = _connect(client)
    novo = "ATATT-novo-token-5555"
    myself(jira, valid_token=novo)

    response = client.put(
        f"{BASE}/{created['id']}", json={**BODY, "api_token": novo}, headers=ALICE
    )

    assert response.status_code == 200
    assert response.json()["token_hint"] == "5555"
    doc = store.docs["uid-alice"][created["id"]]
    assert LocalFernetCipher().decrypt(doc["tokenCiphertext"]) == novo


@pytest.mark.req("F04-RF-05")
def test_trocar_com_credencial_recusada_mantem_a_atual(
    client: TestClient, store: MemoryJiraStore
) -> None:
    created = _connect(client)

    response = client.put(
        f"{BASE}/{created['id']}", json={**BODY, "api_token": "errado-errado"}, headers=ALICE
    )

    assert response.status_code == 422
    doc = store.docs["uid-alice"][created["id"]]
    assert LocalFernetCipher().decrypt(doc["tokenCiphertext"]) == TOKEN


@pytest.mark.req("F04-RF-05")
def test_remover(client: TestClient) -> None:
    created = _connect(client)

    assert client.delete(f"{BASE}/{created['id']}", headers=ALICE).status_code == 204
    assert client.get(BASE, headers=ALICE).json() == []
    assert client.delete(f"{BASE}/{created['id']}", headers=ALICE).status_code == 204


@pytest.mark.req("F04-RF-06")
def test_token_revogado_marca_invalida(client: TestClient, jira: respx.MockRouter) -> None:
    created = _connect(client)
    myself(jira, valid_token="outro-token-que-o-jira-aceita")  # o nosso foi revogado

    response = client.post(f"{BASE}/{created['id']}/validate", headers=ALICE)

    assert response.status_code == 200
    assert response.json()["status"] == "invalid"
    assert client.get(BASE, headers=ALICE).json()[0]["status"] == "invalid"


@pytest.mark.req("F04-RF-06")
def test_testar_conexao_valida_volta_a_ok(client: TestClient, store: MemoryJiraStore) -> None:
    created = _connect(client)
    store.docs["uid-alice"][created["id"]]["status"] = "invalid"

    response = client.post(f"{BASE}/{created['id']}/validate", headers=ALICE)

    assert response.json()["status"] == "ok"


def test_testar_conexao_com_jira_fora_do_ar(client: TestClient, jira: respx.MockRouter) -> None:
    created = _connect(client)
    jira.get(f"{SITE}/rest/api/3/myself").respond(503)

    response = client.post(f"{BASE}/{created['id']}/validate", headers=ALICE)

    assert response.status_code == 502
    assert client.get(BASE, headers=ALICE).json()[0]["status"] == "ok"


def test_conexao_de_outro_usuario_nao_existe(client: TestClient) -> None:
    created = _connect(client, ALICE)
    url = f"{BASE}/{created['id']}"

    assert client.get(BASE, headers=BOB).json() == []
    assert client.post(f"{url}/validate", headers=BOB).status_code == 404
    assert client.put(url, json=BODY, headers=BOB).status_code == 404
    client.delete(url, headers=BOB)
    assert len(client.get(BASE, headers=ALICE).json()) == 1


@pytest.mark.parametrize(
    "body",
    [
        {**BODY, "api_token": "curto"},
        {**BODY, "email": "sem-arroba"},
        {"site_url": SITE, "email": EMAIL},
    ],
)
def test_corpo_invalido_nao_ecoa_o_token(client: TestClient, body: dict[str, str]) -> None:
    response = client.post(BASE, json=body, headers=ALICE)

    assert response.status_code == 422
    assert response.json()["code"] == "validation-error"
    assert "curto" not in response.text


@pytest.mark.req("F04-RT-02")
def test_token_nunca_aparece_nos_logs(
    client: TestClient, jira: respx.MockRouter, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    created = _connect(client)
    client.post(f"{BASE}/{created['id']}/validate", headers=ALICE)
    client.put(f"{BASE}/{created['id']}", json=BODY, headers=ALICE)
    client.post(BASE, json={**BODY, "api_token": "token-errado-0000"}, headers=ALICE)
    myself(jira, valid_token="x" * 20)
    client.post(f"{BASE}/{created['id']}/validate", headers=ALICE)

    assert caplog.records, "o teste precisa capturar algum log para valer"
    assert TOKEN not in caplog.text
    assert "token-errado-0000" not in caplog.text
