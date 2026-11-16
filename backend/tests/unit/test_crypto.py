"""Cifra dos tokens do Jira (F04-RT-01, F04-RT-06)."""

import base64
from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.crypto import CipherError, KmsCipher, LocalFernetCipher, build_cipher

SECRET = "ATATT-segredo-de-teste-1234"


def test_cifra_local_vai_e_volta_sem_texto_em_claro() -> None:
    cipher = LocalFernetCipher()
    encrypted = cipher.encrypt(SECRET)

    assert SECRET.encode() not in encrypted.ciphertext
    assert encrypted.key_version == "local-fernet"
    assert cipher.decrypt(encrypted.ciphertext) == SECRET


def test_ciphertext_corrompido_nao_vaza_o_conteudo() -> None:
    with pytest.raises(CipherError) as exc:
        LocalFernetCipher().decrypt(b"lixo")
    assert SECRET not in str(exc.value)


@pytest.mark.req("F04-RT-06")
@pytest.mark.parametrize("env", ["dev", "stg", "prd"])
def test_cifra_local_proibida_fora_de_local_e_test(
    env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FIREBASE_AUTH_EMULATOR_HOST", raising=False)
    with pytest.raises(RuntimeError):
        build_cipher(env, None)
    with pytest.raises(ValidationError, match="KMS_KEY_NAME"):
        Settings(env=env, kms_key_name=None)


@pytest.mark.req("F04-RT-06")
@pytest.mark.parametrize("env", ["local", "test"])
def test_cifra_local_em_local_e_test(env: str) -> None:
    assert isinstance(build_cipher(env, None), LocalFernetCipher)


def test_chave_local_configuravel() -> None:
    key = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
    encrypted = build_cipher("local", None, key).encrypt(SECRET)

    assert LocalFernetCipher(key.encode()).decrypt(encrypted.ciphertext) == SECRET
    with pytest.raises(CipherError):
        LocalFernetCipher().decrypt(encrypted.ciphertext)


class FakeResponse:
    def __init__(self, status_code: int, data: dict[str, Any]) -> None:
        self.status_code = status_code
        self._data = data

    def json(self) -> dict[str, Any]:
        return self._data


class FakeKms:
    """API REST do KMS em memória: "cifra" invertendo os bytes, só para o teste."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def post(self, url: str, *, json: dict[str, Any], timeout: float) -> FakeResponse:
        self.calls.append((url, json))
        name, _, method = url.removeprefix("https://cloudkms.googleapis.com/v1/").rpartition(":")
        if method == "encrypt":
            raw = base64.b64decode(json["plaintext"])
            return FakeResponse(
                200,
                {
                    "name": f"{name}/cryptoKeyVersions/3",
                    "ciphertext": base64.b64encode(b"kms:" + raw[::-1]).decode(),
                },
            )
        raw = base64.b64decode(json["ciphertext"])
        if not raw.startswith(b"kms:"):
            return FakeResponse(400, {"error": {"message": "bad ciphertext"}})
        return FakeResponse(200, {"plaintext": base64.b64encode(raw[4:][::-1]).decode()})


KEY = "projects/p/locations/us-central1/keyRings/specflow/cryptoKeys/jira-tokens"


@pytest.mark.req("F04-RT-01")
def test_kms_cifra_direto_com_a_chave_e_guarda_a_versao() -> None:
    kms = FakeKms()
    cipher = KmsCipher(KEY, session=kms)

    encrypted = cipher.encrypt(SECRET)

    assert encrypted.key_version == f"{KEY}/cryptoKeyVersions/3"
    assert SECRET.encode() not in encrypted.ciphertext
    assert cipher.decrypt(encrypted.ciphertext) == SECRET
    assert [url for url, _ in kms.calls] == [
        f"https://cloudkms.googleapis.com/v1/{KEY}:encrypt",
        f"https://cloudkms.googleapis.com/v1/{KEY}:decrypt",
    ]
    assert SECRET not in str(kms.calls[0][1])  # vai em base64, nunca como texto


def test_erro_do_kms_nao_vaza_conteudo() -> None:
    with pytest.raises(CipherError) as exc:
        KmsCipher(KEY, session=FakeKms()).decrypt(b"outro")
    assert "400" in str(exc.value)


def test_com_chave_kms_usa_o_kms(monkeypatch: pytest.MonkeyPatch) -> None:
    import google.auth

    monkeypatch.setattr(google.auth, "default", lambda scopes: (object(), "p"))
    assert isinstance(build_cipher("prd", KEY), KmsCipher)
