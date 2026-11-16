"""Dependências das rotas: identidade do token e serviços por requisição."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from google.cloud import firestore

from app.core.auth import FirebaseTokenVerifier, Identity, InvalidTokenError, TokenVerifier
from app.core.config import Settings, get_settings
from app.core.crypto import Cipher, build_cipher
from app.core.errors import EmailNotVerifiedError, UnauthenticatedError
from app.repositories.jira_connections import JiraConnectionRepository
from app.repositories.users import UserRepository
from app.services.account import AccountService
from app.services.jira_connections import JiraConnectionService


@lru_cache
def _verifier(project_id: str, emulator_host: str | None) -> FirebaseTokenVerifier:
    return FirebaseTokenVerifier(project_id, emulator_host=emulator_host)


def get_verifier(settings: Annotated[Settings, Depends(get_settings)]) -> TokenVerifier:
    return _verifier(settings.gcp_project, settings.auth_emulator_host)


@lru_cache
def _firestore(project_id: str, database: str) -> firestore.Client:
    return firestore.Client(project=project_id, database=database)


def get_account_service(settings: Annotated[Settings, Depends(get_settings)]) -> AccountService:
    db = _firestore(settings.gcp_project, settings.firestore_database)
    return AccountService(UserRepository(db))


@lru_cache
def _cipher(env: str, kms_key_name: str | None, local_key: str | None) -> Cipher:
    return build_cipher(env, kms_key_name, local_key)


def get_jira_service(settings: Annotated[Settings, Depends(get_settings)]) -> JiraConnectionService:
    db = _firestore(settings.gcp_project, settings.firestore_database)
    return JiraConnectionService(
        JiraConnectionRepository(db),
        _cipher(settings.env, settings.kms_key_name, settings.local_cipher_key),
    )


def _bearer(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise UnauthenticatedError()
    return token.strip()


def _identity(
    authorization: str | None, verifier: TokenVerifier, *, check_revoked: bool
) -> Identity:
    try:
        identity = verifier.verify(_bearer(authorization), check_revoked=check_revoked)
    except InvalidTokenError as exc:
        raise UnauthenticatedError("Sua sessão expirou ou é inválida. Entre de novo.") from exc
    if identity.needs_email_verification:
        raise EmailNotVerifiedError()
    return identity


def current_user(
    verifier: Annotated[TokenVerifier, Depends(get_verifier)],
    authorization: Annotated[str | None, Header()] = None,
) -> Identity:
    """Identidade da requisição. O `uid` vem só do token, nunca de corpo/rota/query (F03-RT-02)."""
    return _identity(authorization, verifier, check_revoked=False)


def current_user_checked(
    verifier: Annotated[TokenVerifier, Depends(get_verifier)],
    authorization: Annotated[str | None, Header()] = None,
) -> Identity:
    """Como `current_user`, mas recusa token revogado; usada em rotas sensíveis (F03-RT-01)."""
    return _identity(authorization, verifier, check_revoked=True)


CurrentUser = Annotated[Identity, Depends(current_user)]
CurrentUserChecked = Annotated[Identity, Depends(current_user_checked)]
Account = Annotated[AccountService, Depends(get_account_service)]
JiraConnections = Annotated[JiraConnectionService, Depends(get_jira_service)]
