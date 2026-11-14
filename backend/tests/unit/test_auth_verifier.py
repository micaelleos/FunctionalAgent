"""FirebaseTokenVerifier com tokens RS256 assinados por uma chave de teste (F03-RT-01).

Cobre o que o emulador não confere: assinatura, `kid`, expiração e revogação.
"""

import datetime as dt
from typing import Any

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from google.auth import crypt, jwt

from app.core.auth import FirebaseTokenVerifier, InvalidTokenError, identity_from_claims

PROJECT = "pcb-inspect"
NOW = 1_800_000_000


def _key_and_cert() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "securetoken-teste")])
    start = dt.datetime.fromtimestamp(NOW - 86400, tz=dt.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(start)
        .not_valid_after(start + dt.timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return key_pem, cert.public_bytes(serialization.Encoding.PEM).decode()


KEY_PEM, CERT_PEM = _key_and_cert()
OTHER_KEY_PEM, _ = _key_and_cert()


def make_token(key_pem: str = KEY_PEM, kid: str = "k1", **overrides: Any) -> str:
    claims: dict[str, Any] = {
        "aud": PROJECT,
        "iss": f"https://securetoken.google.com/{PROJECT}",
        "sub": "uid-alice",
        "iat": NOW - 60,
        "exp": NOW + 3540,
        "auth_time": NOW - 60,
        "email": "alice@teste.dev",
        "email_verified": True,
        "name": "Alice",
        "firebase": {"sign_in_provider": "google.com"},
    }
    claims.update(overrides)
    signer = crypt.RSASigner.from_string(key_pem, key_id=kid)  # type: ignore[no-untyped-call]
    token: bytes = jwt.encode(signer, claims)  # type: ignore[no-untyped-call]
    return token.decode()


class Clock:
    def __init__(self) -> None:
        self.now = float(NOW)

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    # google-auth confere exp/iat com o relógio real; fixamos os dois no mesmo instante.
    c = Clock()
    monkeypatch.setattr(
        "google.auth._helpers.utcnow",
        lambda: dt.datetime.fromtimestamp(c.now, tz=dt.UTC).replace(tzinfo=None),
    )
    return c


@pytest.fixture
def fetches() -> list[int]:
    return []


@pytest.fixture
def users() -> dict[str, dict[str, Any]]:
    return {"uid-alice": {"localId": "uid-alice", "validSince": str(NOW - 3600)}}


@pytest.fixture
def verifier(
    clock: Clock, fetches: list[int], users: dict[str, dict[str, Any]]
) -> FirebaseTokenVerifier:
    def fetch() -> tuple[dict[str, str], int]:
        fetches.append(1)
        return {"k1": CERT_PEM}, 600

    return FirebaseTokenVerifier(PROJECT, fetch_certs=fetch, lookup_user=users.get, clock=clock)


def test_token_valido_vira_identidade(verifier: FirebaseTokenVerifier) -> None:
    identity = verifier.verify(make_token())

    assert identity.uid == "uid-alice"
    assert identity.email == "alice@teste.dev"
    assert identity.sign_in_provider == "google.com"


@pytest.mark.parametrize(
    ("label", "token"),
    [
        ("outra-chave", lambda: make_token(OTHER_KEY_PEM)),
        ("kid-desconhecido", lambda: make_token(kid="k9")),
        ("expirado", lambda: make_token(iat=NOW - 7200, exp=NOW - 3600)),
        ("futuro", lambda: make_token(iat=NOW + 3600, exp=NOW + 7200)),
        ("outro-projeto", lambda: make_token(aud="outro")),
        ("outro-emissor", lambda: make_token(iss="https://securetoken.google.com/outro")),
        ("sem-sub", lambda: make_token(sub="")),
        ("malformado", lambda: "abc.def"),
    ],
)
def test_token_invalido_e_recusado(verifier: FirebaseTokenVerifier, label: str, token: Any) -> None:
    with pytest.raises(InvalidTokenError):
        verifier.verify(token())


def test_token_sem_assinatura_e_recusado_fora_do_emulador(
    verifier: FirebaseTokenVerifier,
) -> None:
    _, payload, _ = make_token().split(".")
    unsigned_header = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0"  # {"alg":"none","typ":"JWT"}

    with pytest.raises(InvalidTokenError):
        verifier.verify(f"{unsigned_header}.{payload}.")


def test_certificados_ficam_em_cache_ate_o_max_age(
    verifier: FirebaseTokenVerifier, clock: Clock, fetches: list[int]
) -> None:
    verifier.verify(make_token())
    verifier.verify(make_token())
    assert len(fetches) == 1

    clock.now += 601
    verifier.verify(make_token(iat=NOW + 541, exp=NOW + 4141, auth_time=NOW + 541))
    assert len(fetches) == 2


def test_revogacao_so_e_conferida_quando_pedida(
    verifier: FirebaseTokenVerifier, users: dict[str, dict[str, Any]]
) -> None:
    users["uid-alice"]["validSince"] = str(NOW)  # sessões anteriores a NOW foram revogadas
    token = make_token()

    assert verifier.verify(token).uid == "uid-alice"
    with pytest.raises(InvalidTokenError, match="revogada"):
        verifier.verify(token, check_revoked=True)


@pytest.mark.parametrize("state", ["desativada", "inexistente"])
def test_conta_desativada_ou_inexistente_e_recusada_na_revogacao(
    verifier: FirebaseTokenVerifier, users: dict[str, dict[str, Any]], state: str
) -> None:
    if state == "desativada":
        users["uid-alice"]["disabled"] = True
    else:
        users.clear()

    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(), check_revoked=True)


def test_emulador_aceita_token_sem_assinatura_mas_confere_as_claims(clock: Clock) -> None:
    verifier = FirebaseTokenVerifier(PROJECT, emulator_host="localhost:9099", clock=clock)
    _, payload, _ = make_token().split(".")
    _, expired, _ = make_token(iat=NOW - 7200, exp=NOW - 3600).split(".")
    unsigned = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0"

    assert verifier.verify(f"{unsigned}.{payload}.").uid == "uid-alice"
    with pytest.raises(InvalidTokenError, match="expirado"):
        verifier.verify(f"{unsigned}.{expired}.")


def test_conta_de_senha_sem_verificacao_precisa_verificar() -> None:
    claims = {"sub": "u", "email_verified": False, "firebase": {"sign_in_provider": "password"}}

    assert identity_from_claims(claims).needs_email_verification
    assert not identity_from_claims({**claims, "email_verified": True}).needs_email_verification
