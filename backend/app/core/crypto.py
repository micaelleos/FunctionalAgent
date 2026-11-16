"""Cifra dos tokens do Jira (ADR-004, F04-RT-01, F04-RT-06).

Produção usa `kms.encrypt` direto com a chave `jira-tokens` (o token tem bem menos de 64 KiB).
O Firestore guarda só o ciphertext e a versão da chave. `LocalFernetCipher` existe para
`make dev` e os testes e só é criada com `ENV` `local` ou `test`.
"""

import base64
from dataclasses import dataclass
from typing import Any, Protocol

from cryptography.fernet import Fernet, InvalidToken

# Chave fixa só para desenvolvimento local e testes; nunca protege dado real.
_DEV_FERNET_KEY = b"c3BlY2Zsb3ctZGV2LW9ubHktbm90LWEtc2VjcmV0ISE="


@dataclass(frozen=True)
class Encrypted:
    ciphertext: bytes
    key_version: str


class CipherError(Exception):
    """Falha ao cifrar ou decifrar. A mensagem nunca contém o texto em claro."""


class Cipher(Protocol):
    def encrypt(self, plaintext: str) -> Encrypted: ...
    def decrypt(self, ciphertext: bytes) -> str: ...


class LocalFernetCipher:
    def __init__(self, key: bytes = _DEV_FERNET_KEY) -> None:
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> Encrypted:
        return Encrypted(self._fernet.encrypt(plaintext.encode()), "local-fernet")

    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._fernet.decrypt(ciphertext).decode()
        except InvalidToken as exc:
            raise CipherError("não foi possível decifrar o token") from exc


class HttpSession(Protocol):
    def post(self, url: str, *, json: dict[str, Any], timeout: float) -> Any: ...


_KMS_API = "https://cloudkms.googleapis.com/v1"


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


class KmsCipher:
    """Cloud KMS pela API REST (`google-auth`), sem a biblioteca gRPC, que estourava o limite de
    300 MB da imagem. A SA de runtime tem `cryptoKeyEncrypterDecrypter` só nesta chave (F02).
    """

    def __init__(self, key_name: str, session: HttpSession | None = None) -> None:
        self._key = key_name
        if session is None:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession

            credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloudkms"]
            )
            session = AuthorizedSession(credentials)  # type: ignore[no-untyped-call]
        self._session = session

    def _call(self, method: str, body: dict[str, Any]) -> dict[str, Any]:
        response = self._session.post(f"{_KMS_API}/{self._key}:{method}", json=body, timeout=10.0)
        if response.status_code != 200:
            # Só o status: o corpo do erro pode repetir parte da requisição.
            raise CipherError(f"KMS {method} respondeu {response.status_code}")
        data: dict[str, Any] = response.json()
        return data

    def encrypt(self, plaintext: str) -> Encrypted:
        data = self._call("encrypt", {"plaintext": _b64(plaintext.encode())})
        # `name` é a versão usada (…/cryptoKeyVersions/N); a rotação mantém as antigas decifrando.
        return Encrypted(base64.b64decode(data["ciphertext"]), str(data["name"]))

    def decrypt(self, ciphertext: bytes) -> str:
        data = self._call("decrypt", {"ciphertext": _b64(ciphertext)})
        return base64.b64decode(data["plaintext"]).decode()


def build_cipher(env: str, kms_key_name: str | None, local_key: str | None = None) -> Cipher:
    """KMS quando há chave; cifra local só em `local`/`test` (F04-RT-06)."""
    if kms_key_name:
        return KmsCipher(kms_key_name)
    if env not in {"local", "test"}:
        # Settings já recusa isso; a checagem repetida protege quem montar a cifra sem Settings.
        raise RuntimeError(f"cifra local proibida com ENV={env}")
    return LocalFernetCipher(local_key.encode() if local_key else _DEV_FERNET_KEY)
