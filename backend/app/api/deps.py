"""Dependências das rotas: identidade do token e serviços por requisição."""

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from google.cloud import firestore
from langchain_core.language_models import BaseChatModel

from app.agent.llm import build_chat_model
from app.core.app_check import (
    AppCheckVerifier,
    FirebaseAppCheckVerifier,
    InvalidAppCheckTokenError,
)
from app.core.auth import FirebaseTokenVerifier, Identity, InvalidTokenError, TokenVerifier
from app.core.config import Settings, get_settings
from app.core.crypto import Cipher, build_cipher
from app.core.errors import AppCheckRequiredError, EmailNotVerifiedError, UnauthenticatedError
from app.core.logging import bind, uid_hash
from app.repositories.actions import ActionRepository
from app.repositories.jira_cache import JiraCacheRepository
from app.repositories.jira_connections import JiraConnectionRepository
from app.repositories.usage import UsageRepository
from app.repositories.users import UserRepository
from app.services.account import AccountService
from app.services.actions import ActionService
from app.services.chat import ChatService, shared_agent
from app.services.conversations import ConversationService
from app.services.jira_connections import JiraConnectionService
from app.services.jira_issues import JiraIssueService
from app.services.jira_projects import JiraProjectService
from app.services.usage import UsageService

log = logging.getLogger("app.auth")


@lru_cache
def _verifier(project_id: str, emulator_host: str | None) -> FirebaseTokenVerifier:
    return FirebaseTokenVerifier(project_id, emulator_host=emulator_host)


def get_verifier(settings: Annotated[Settings, Depends(get_settings)]) -> TokenVerifier:
    return _verifier(settings.gcp_project, settings.auth_emulator_host)


@lru_cache
def _app_check(project_number: str, project_id: str) -> FirebaseAppCheckVerifier:
    return FirebaseAppCheckVerifier(project_number, project_id)


def get_app_check_verifier(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AppCheckVerifier | None:
    if settings.app_check_mode == "off" or not settings.firebase_project_number:
        return None
    return _app_check(settings.firebase_project_number, settings.gcp_project)


def _check_app(mode: str, verifier: AppCheckVerifier | None, token: str | None) -> None:
    """App Check (F11-RT-07): `monitor` só registra; `enforce` recusa com 401."""
    if mode == "off" or verifier is None:
        return
    if not token:
        result = "missing"
    else:
        try:
            verifier.verify(token)
            return
        except InvalidAppCheckTokenError:
            result = "invalid"
    log.warning(
        "app_check", extra={"fields": {"event": "app_check", "result": result, "mode": mode}}
    )
    if mode == "enforce":
        raise AppCheckRequiredError()


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


def get_jira_project_service(
    settings: Annotated[Settings, Depends(get_settings)],
    jira: Annotated[JiraConnectionService, Depends(get_jira_service)],
) -> JiraProjectService:
    db = _firestore(settings.gcp_project, settings.firestore_database)
    return JiraProjectService(jira, JiraCacheRepository(db))


def get_jira_issue_service(
    settings: Annotated[Settings, Depends(get_settings)],
    jira: Annotated[JiraConnectionService, Depends(get_jira_service)],
) -> JiraIssueService:
    db = _firestore(settings.gcp_project, settings.firestore_database)
    return JiraIssueService(ActionRepository(db), jira)


_models: dict[tuple[str, ...], BaseChatModel] = {}


def _chat_model(settings: Settings) -> BaseChatModel:
    # O modelo não guarda estado de conversa (só configuração): pode ser compartilhado.
    key = (
        settings.llm_provider,
        settings.llm_model,
        settings.llm_location,
        settings.llm_project or settings.gcp_project,
    )
    if key not in _models:
        _models[key] = build_chat_model(settings)
    return _models[key]


def get_chat_service(
    settings: Annotated[Settings, Depends(get_settings)],
    jira: Annotated[JiraConnectionService, Depends(get_jira_service)],
) -> ChatService:
    db = _firestore(settings.gcp_project, settings.firestore_database)
    llm = _chat_model(settings)
    title_llm = llm if settings.auto_title_enabled else None
    usage = UsageService(UsageRepository(db), settings)
    return ChatService(
        ActionRepository(db),
        jira,
        llm,
        settings,
        title_llm=title_llm,
        usage=usage,
        agent=shared_agent(llm, settings.agent_max_iterations),
    )


def get_usage_service(settings: Annotated[Settings, Depends(get_settings)]) -> UsageService:
    db = _firestore(settings.gcp_project, settings.firestore_database)
    return UsageService(UsageRepository(db), settings)


def get_conversation_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConversationService:
    db = _firestore(settings.gcp_project, settings.firestore_database)
    return ConversationService(ActionRepository(db))


def get_action_service(
    settings: Annotated[Settings, Depends(get_settings)],
    jira: Annotated[JiraConnectionService, Depends(get_jira_service)],
) -> ActionService:
    """Sem modelo de linguagem: a execução não passa pelo LLM (F06-RT-03)."""
    db = _firestore(settings.gcp_project, settings.firestore_database)
    return ActionService(ActionRepository(db), jira, settings)


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
    bind(uid_hash=uid_hash(identity.uid))  # logs da requisição sem o uid (F11-RT-01)
    if identity.needs_email_verification:
        raise EmailNotVerifiedError()
    return identity


AppCheckHeader = Annotated[str | None, Header(alias="X-Firebase-AppCheck")]


def current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    verifier: Annotated[TokenVerifier, Depends(get_verifier)],
    app_check: Annotated[AppCheckVerifier | None, Depends(get_app_check_verifier)],
    authorization: Annotated[str | None, Header()] = None,
    app_check_token: AppCheckHeader = None,
) -> Identity:
    """Identidade da requisição. O `uid` vem só do token, nunca de corpo/rota/query (F03-RT-02)."""
    identity = _identity(authorization, verifier, check_revoked=False)
    _check_app(settings.app_check_mode, app_check, app_check_token)
    return identity


def current_user_checked(
    settings: Annotated[Settings, Depends(get_settings)],
    verifier: Annotated[TokenVerifier, Depends(get_verifier)],
    app_check: Annotated[AppCheckVerifier | None, Depends(get_app_check_verifier)],
    authorization: Annotated[str | None, Header()] = None,
    app_check_token: AppCheckHeader = None,
) -> Identity:
    """Como `current_user`, mas recusa token revogado; usada em rotas sensíveis (F03-RT-01)."""
    identity = _identity(authorization, verifier, check_revoked=True)
    _check_app(settings.app_check_mode, app_check, app_check_token)
    return identity


CurrentUser = Annotated[Identity, Depends(current_user)]
CurrentUserChecked = Annotated[Identity, Depends(current_user_checked)]
Account = Annotated[AccountService, Depends(get_account_service)]
JiraConnections = Annotated[JiraConnectionService, Depends(get_jira_service)]
Chat = Annotated[ChatService, Depends(get_chat_service)]
Actions = Annotated[ActionService, Depends(get_action_service)]
Conversations = Annotated[ConversationService, Depends(get_conversation_service)]
JiraProjects = Annotated[JiraProjectService, Depends(get_jira_project_service)]
JiraIssues = Annotated[JiraIssueService, Depends(get_jira_issue_service)]
Usage = Annotated[UsageService, Depends(get_usage_service)]
