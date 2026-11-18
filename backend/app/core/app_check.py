"""Verificação do token do Firebase App Check (F11-RT-07).

O SPA manda `X-Firebase-AppCheck` (reCAPTCHA Enterprise). Como no `auth.py`, sem `firebase-admin`
(limite da imagem): o token é um JWT RS256 assinado com as chaves de
`https://firebaseappcheck.googleapis.com/v1/jwks`, com `iss` igual a
`https://firebaseappcheck.googleapis.com/<número do projeto>` e `aud` contendo
`projects/<número do projeto>`. O `sub` é o id do app web que pediu o token.
"""

import base64
import time
from collections.abc import Callable
from typing import Any, Protocol

import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from google.auth import jwt

from app.core.auth import _CertCache

JWKS_URL = "https://firebaseappcheck.googleapis.com/v1/jwks"
ISSUER_PREFIX = "https://firebaseappcheck.googleapis.com/"
_JWKS_TTL_S = 6 * 3600  # recomendação do Firebase para o cache das chaves
_TIMEOUT_S = 5
_CLOCK_SKEW_S = 10


class InvalidAppCheckTokenError(Exception):
    """Token do App Check ausente, malformado, expirado ou de outro projeto/app."""


class AppCheckVerifier(Protocol):
    def verify(self, token: str) -> str: ...


def _b64int(value: str) -> int:
    return int.from_bytes(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)), "big")


def jwk_to_pem(key: dict[str, Any]) -> str:
    numbers = RSAPublicNumbers(_b64int(key["e"]), _b64int(key["n"]))
    pem = numbers.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem.decode()


def fetch_app_check_keys() -> tuple[dict[str, str], int]:
    response = requests.get(JWKS_URL, timeout=_TIMEOUT_S)
    response.raise_for_status()
    keys = response.json().get("keys") or []
    return {k["kid"]: jwk_to_pem(k) for k in keys if k.get("kty") == "RSA"}, _JWKS_TTL_S


class FirebaseAppCheckVerifier:
    def __init__(
        self,
        project_number: str,
        project_id: str,
        *,
        fetch_keys: Callable[[], tuple[dict[str, str], int]] = fetch_app_check_keys,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._number = project_number
        self._project_id = project_id
        self._keys = _CertCache(fetch_keys, clock)
        self._clock = clock

    def verify(self, token: str) -> str:
        """Devolve o id do app (`sub`) ou levanta `InvalidAppCheckTokenError`."""
        try:
            header = jwt.decode_header(token)  # type: ignore[no-untyped-call]
            if header.get("alg") != "RS256" or header.get("typ") != "JWT" or not header.get("kid"):
                raise ValueError("cabeçalho inválido")
            # `aud` é uma lista: conferida abaixo, não pelo google-auth.
            claims: dict[str, Any] = jwt.decode(  # type: ignore[no-untyped-call]
                token, certs=self._keys.get(), clock_skew_in_seconds=_CLOCK_SKEW_S
            )
            if claims.get("iss") != ISSUER_PREFIX + self._number:
                raise ValueError("emissor inválido (iss)")
            audience = claims.get("aud")
            if not isinstance(audience, list) or f"projects/{self._number}" not in audience:
                raise ValueError("token de outro projeto (aud)")
            if not isinstance(claims.get("sub"), str) or not claims["sub"]:
                raise ValueError("sub inválido")
            if int(claims["exp"]) < self._clock() - _CLOCK_SKEW_S:
                raise ValueError("token expirado")
        except (ValueError, KeyError, TypeError) as exc:
            raise InvalidAppCheckTokenError(str(exc)) from exc
        return str(claims["sub"])
