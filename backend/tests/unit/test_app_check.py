"""App Check (F11-RT-07): verificação do token e os modos off/monitor/enforce."""

import base64
import logging
import time
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from google.auth import crypt, jwt

from app.api.deps import get_app_check_verifier, get_verifier
from app.core.app_check import (
    FirebaseAppCheckVerifier,
    InvalidAppCheckTokenError,
    jwk_to_pem,
)
from app.core.config import Settings, get_settings
from app.main import create_app
from tests.fakes import FakeVerifier

pytestmark = pytest.mark.req("F11-RT-07")

NUMBER = "123456789"
APP_ID = "1:123456789:web:abc"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _pem(key: rsa.RSAPrivateKey) -> str:
    return (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )


def _token(key: rsa.RSAPrivateKey = KEY, **claims: Any) -> str:
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    signer = crypt.RSASigner.from_string(private, key_id="k1")  # type: ignore[no-untyped-call]
    now = int(time.time())
    payload = {
        "iss": f"https://firebaseappcheck.googleapis.com/{NUMBER}",
        "aud": [f"projects/{NUMBER}", "projects/pcb-inspect"],
        "sub": APP_ID,
        "iat": now,
        "exp": now + 3600,
        **claims,
    }
    encoded: bytes = jwt.encode(signer, payload, header={"typ": "JWT"})  # type: ignore[no-untyped-call]
    return encoded.decode()


def _verifier() -> FirebaseAppCheckVerifier:
    return FirebaseAppCheckVerifier(
        NUMBER, "pcb-inspect", fetch_keys=lambda: ({"k1": _pem(KEY)}, 3600)
    )


def test_token_valido_devolve_o_app() -> None:
    assert _verifier().verify(_token()) == APP_ID


@pytest.mark.parametrize(
    ("label", "token"),
    [
        ("assinatura de outra chave", lambda: _token(OTHER)),
        ("outro projeto", lambda: _token(aud=["projects/999"])),
        ("outro emissor", lambda: _token(iss="https://evil.example/123456789")),
        ("expirado", lambda: _token(iat=int(time.time()) - 7200, exp=int(time.time()) - 3600)),
        ("lixo", lambda: "nao.e.jwt"),
    ],
)
def test_token_invalido(label: str, token: Any) -> None:
    with pytest.raises(InvalidAppCheckTokenError):
        _verifier().verify(token())


def test_jwk_vira_pem() -> None:
    numbers = KEY.public_key().public_numbers()

    def b64(n: int) -> str:
        raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    assert jwk_to_pem({"kty": "RSA", "n": b64(numbers.n), "e": b64(numbers.e)}) == _pem(KEY)


def _client(mode: str) -> TestClient:
    app = create_app()
    settings = Settings(env="test", app_check_mode=mode, firebase_project_number=NUMBER)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_verifier] = FakeVerifier
    app.dependency_overrides[get_app_check_verifier] = _verifier
    return TestClient(app)


AUTH = {"Authorization": "Bearer ok:alice"}


def test_enforce_recusa_sem_app_check() -> None:
    with _client("enforce") as client:
        missing = client.get("/api/v1/me/usage", headers=AUTH)
        invalid = client.get(
            "/api/v1/me/usage", headers={**AUTH, "X-Firebase-AppCheck": _token(OTHER)}
        )

    for response in (missing, invalid):
        assert response.status_code == 401
        assert response.json()["code"] == "app-check-required"


def test_enforce_aceita_com_app_check(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api import deps
    from app.services.usage import UsageService
    from tests.chat_fakes import MemoryChatStore

    usage = UsageService(MemoryChatStore(), Settings(env="test"))
    with _client("enforce") as client:
        client.app.dependency_overrides[deps.get_usage_service] = lambda: usage  # type: ignore[attr-defined]
        ok = client.get("/api/v1/me/usage", headers={**AUTH, "X-Firebase-AppCheck": _token()})

    assert ok.status_code == 200


def test_monitor_so_registra(caplog: pytest.LogCaptureFixture) -> None:
    from app.api import deps
    from app.services.usage import UsageService
    from tests.chat_fakes import MemoryChatStore

    caplog.set_level(logging.WARNING, logger="app.auth")
    usage = UsageService(MemoryChatStore(), Settings(env="test"))
    with _client("monitor") as client:
        client.app.dependency_overrides[deps.get_usage_service] = lambda: usage  # type: ignore[attr-defined]
        response = client.get("/api/v1/me/usage", headers=AUTH)

    assert response.status_code == 200
    [record] = [r for r in caplog.records if getattr(r, "fields", {}).get("event") == "app_check"]
    assert getattr(record, "fields") == {  # noqa: B009
        "event": "app_check",
        "result": "missing",
        "mode": "monitor",
    }


def test_modo_sem_numero_do_projeto_nao_sobe() -> None:
    with pytest.raises(ValueError, match="FIREBASE_PROJECT_NUMBER"):
        Settings(env="test", app_check_mode="monitor")
