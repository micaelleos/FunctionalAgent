"""Verificação do ID token do Firebase Auth (F03-RT-01).

O Auth é o do projeto compartilhado do portfólio (`pcb-inspect`): o mesmo login vale nos outros
apps, então este módulo só *lê* a identidade; nunca apaga usuários nem revoga sessões (F03-RT-04).

Usa `google-auth` em vez do `firebase-admin`, que traz o `googleapiclient` (+110 MB) e estoura o
limite de 300 MB da imagem (F01-RT-05). As regras são as mesmas do Admin SDK:
- assinatura RS256 com os certificados públicos do `securetoken`, em cache conforme o
  `Cache-Control`;
- `aud` igual ao projeto e `iss` igual a `https://securetoken.google.com/<projeto>`;
- `exp`/`iat` válidos e `sub` não vazio;
- revogação (opcional) pelo `validSince` da conta.
"""

import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import google.auth
import google.auth.transport.requests
import requests
from google.auth import jwt

CERTS_URL = (
    "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
)
ISSUER_PREFIX = "https://securetoken.google.com/"
_CLOCK_SKEW_S = 10
_DEFAULT_CERT_TTL_S = 3600
_TIMEOUT_S = 5


@dataclass(frozen=True)
class Identity:
    """Quem fez a requisição, tirado *somente* do token (F03-RT-02)."""

    uid: str
    email: str | None
    email_verified: bool
    name: str | None
    sign_in_provider: str

    @property
    def needs_email_verification(self) -> bool:
        # Contas de e-mail/senha só usam o app depois de verificar o e-mail (F03-RF-02, F03-RT-07).
        return self.sign_in_provider == "password" and not self.email_verified


class InvalidTokenError(Exception):
    """Token ausente, malformado, expirado, revogado, de conta desativada ou de outro projeto."""


class TokenVerifier(Protocol):
    def verify(self, token: str, *, check_revoked: bool = False) -> Identity: ...


def identity_from_claims(claims: dict[str, Any]) -> Identity:
    firebase_claims = claims.get("firebase") or {}
    return Identity(
        uid=str(claims["sub"]),
        email=claims.get("email"),
        email_verified=bool(claims.get("email_verified", False)),
        name=claims.get("name"),
        sign_in_provider=str(firebase_claims.get("sign_in_provider", "unknown")),
    )


CertFetcher = Callable[[], tuple[dict[str, str], int]]
UserLookup = Callable[[str], dict[str, Any] | None]


def fetch_google_certs() -> tuple[dict[str, str], int]:
    """Certificados públicos do securetoken e por quantos segundos valem (`max-age`)."""
    response = requests.get(CERTS_URL, timeout=_TIMEOUT_S)
    response.raise_for_status()
    match = re.search(r"max-age=(\d+)", response.headers.get("Cache-Control", ""))
    certs: dict[str, str] = response.json()
    return certs, int(match.group(1)) if match else _DEFAULT_CERT_TTL_S


class _CertCache:
    def __init__(self, fetch: CertFetcher, clock: Callable[[], float]) -> None:
        self._fetch = fetch
        self._clock = clock
        self._lock = threading.Lock()
        self._certs: dict[str, str] = {}
        self._expires_at = 0.0

    def get(self) -> dict[str, str]:
        with self._lock:
            if self._clock() >= self._expires_at:
                self._certs, ttl = self._fetch()
                self._expires_at = self._clock() + ttl
            return self._certs


def identity_toolkit_lookup(project_id: str, emulator_host: str | None) -> UserLookup:
    """Consulta a conta (`validSince`, `disabled`) na API do Identity Toolkit."""
    if emulator_host:
        base = f"http://{emulator_host}/identitytoolkit.googleapis.com"
        session: requests.Session = requests.Session()
        session.headers["Authorization"] = "Bearer owner"
    else:
        base = "https://identitytoolkit.googleapis.com"
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        session = google.auth.transport.requests.AuthorizedSession(credentials)  # type: ignore[no-untyped-call]

    def lookup(uid: str) -> dict[str, Any] | None:
        response = session.post(
            f"{base}/v1/projects/{project_id}/accounts:lookup",
            json={"localId": [uid]},
            timeout=_TIMEOUT_S,
        )
        response.raise_for_status()
        users: list[dict[str, Any]] = response.json().get("users", [])
        return users[0] if users else None

    return lookup


class FirebaseTokenVerifier:
    """Valida ID tokens do Firebase do projeto `project_id`.

    Com `emulator_host` (só fora de produção), aceita os tokens sem assinatura do emulador de
    Auth, mas continua conferindo `aud`, `iss`, `exp` e `sub`.
    """

    def __init__(
        self,
        project_id: str,
        *,
        emulator_host: str | None = None,
        fetch_certs: CertFetcher = fetch_google_certs,
        lookup_user: UserLookup | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._project_id = project_id
        self._emulator = emulator_host
        self._certs = _CertCache(fetch_certs, clock)
        self._lookup = lookup_user
        self._clock = clock

    def verify(self, token: str, *, check_revoked: bool = False) -> Identity:
        try:
            claims = self._decode(token)
            self._check_claims(claims)
        except (ValueError, KeyError, TypeError) as exc:
            # google-auth sinaliza assinatura, formato e expiração inválidos com ValueError.
            raise InvalidTokenError(str(exc)) from exc
        if check_revoked:
            self._check_not_revoked(claims)
        return identity_from_claims(claims)

    def _decode(self, token: str) -> dict[str, Any]:
        if self._emulator:
            claims: dict[str, Any] = jwt.decode(token, verify=False)  # type: ignore[no-untyped-call]
            return claims
        header = jwt.decode_header(token)  # type: ignore[no-untyped-call]
        if header.get("alg") != "RS256" or not header.get("kid"):
            raise ValueError("cabeçalho do token inválido")
        claims = jwt.decode(  # type: ignore[no-untyped-call]
            token,
            certs=self._certs.get(),
            audience=self._project_id,
            clock_skew_in_seconds=_CLOCK_SKEW_S,
        )
        return claims

    def _check_claims(self, claims: dict[str, Any]) -> None:
        now = self._clock()
        if claims.get("aud") != self._project_id:
            raise ValueError("token de outro projeto (aud)")
        if claims.get("iss") != ISSUER_PREFIX + self._project_id:
            raise ValueError("emissor inválido (iss)")
        if not isinstance(claims.get("sub"), str) or not claims["sub"] or len(claims["sub"]) > 128:
            raise ValueError("sub inválido")
        if int(claims["exp"]) < now - _CLOCK_SKEW_S:
            raise ValueError("token expirado")
        if int(claims["iat"]) > now + _CLOCK_SKEW_S:
            raise ValueError("token emitido no futuro")

    def _check_not_revoked(self, claims: dict[str, Any]) -> None:
        if self._lookup is None:
            self._lookup = identity_toolkit_lookup(self._project_id, self._emulator)
        user = self._lookup(str(claims["sub"]))
        if user is None or user.get("disabled"):
            raise InvalidTokenError("conta inexistente ou desativada")
        if int(claims.get("auth_time", 0)) < int(user.get("validSince", 0)):
            raise InvalidTokenError("sessão revogada")
