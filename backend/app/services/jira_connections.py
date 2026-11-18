"""Conexão de cada usuário com o Jira (F04): validar, cifrar, guardar, testar e remover.

O token chega em claro só no corpo do POST/PUT, é validado no Jira, cifrado (KMS) e descartado.
Nenhuma resposta nem log o contém (F04-RT-02). `client_for` decifra por requisição e é a porta
de entrada de F05/F09/F10 para falar com o Jira em nome do usuário (F04-RT-05).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, SecretStr, field_validator

from app.core.crypto import Cipher
from app.core.errors import ApiProblemError
from app.core.telemetry import in_thread
from app.integrations.jira.client import (
    JiraAccount,
    JiraAuthError,
    JiraClient,
    JiraError,
)
from app.integrations.jira.urls import InvalidSiteUrlError, normalize_site_url

ConnectionStatus = Literal["ok", "invalid"]


class JiraConnectionInput(BaseModel):
    site_url: str = Field(max_length=300, examples=["https://sua-empresa.atlassian.net"])
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+$")
    api_token: SecretStr = Field(min_length=8, max_length=2048)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return value.strip()


class JiraConnection(BaseModel):
    """O que a API devolve: nunca o token, só os 4 últimos caracteres (F04-RF-04)."""

    id: str
    site_url: str
    email: str
    account_name: str
    token_hint: str
    status: ConnectionStatus
    last_validated_at: datetime


class InvalidSiteError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(
            422,
            "jira-invalid-url",
            "URL do Jira inválida",
            "Informe uma URL https://<seu-site>.atlassian.net",
        )


class InvalidCredentialsError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(
            422,
            "jira-invalid-credentials",
            "Credencial recusada pelo Jira",
            "O Jira recusou a credencial. Verifique e-mail e token.",
        )


class UnreachableError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(
            502,
            "jira-unreachable",
            "Jira inacessível",
            "Não conseguimos falar com esse site do Jira. Confira a URL e tente de novo.",
        )


class ConnectionExistsError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(
            409,
            "jira-connection-exists",
            "Já existe uma conexão",
            "Você já tem uma conexão com o Jira. Troque a credencial ou remova a atual.",
        )


class ConnectionNotFoundError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(404, "jira-connection-not-found", "Conexão não encontrada")


class ConnectionStore(Protocol):
    def list(self, uid: str) -> list[dict[str, Any]]: ...
    def get(self, uid: str, connection_id: str) -> dict[str, Any] | None: ...
    def create(self, uid: str, data: dict[str, Any]) -> str: ...
    def update(self, uid: str, connection_id: str, data: dict[str, Any]) -> None: ...
    def delete(self, uid: str, connection_id: str) -> None: ...


ClientFactory = Callable[[str, str, str], JiraClient]


def _hint(token: str) -> str:
    return token[-4:]


def _out(doc: dict[str, Any]) -> JiraConnection:
    return JiraConnection(
        id=doc["id"],
        site_url=doc["siteUrl"],
        email=doc["email"],
        account_name=doc["accountName"],
        token_hint=doc["tokenHint"],
        status=doc["status"],
        last_validated_at=doc["lastValidatedAt"],
    )


class JiraConnectionService:
    def __init__(
        self,
        store: ConnectionStore,
        cipher: Cipher,
        client_factory: ClientFactory = JiraClient,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._cipher = cipher
        self._client_factory = client_factory
        self._clock = clock or (lambda: datetime.now(UTC))

    # Firestore e KMS são síncronos: rodam numa thread para não travar o event loop.
    async def _run[T](self, fn: Callable[..., T], *args: Any) -> T:
        return await in_thread(fn, *args)

    async def list(self, uid: str) -> list[JiraConnection]:
        return [_out(doc) for doc in await self._run(self._store.list, uid)]

    async def _get(self, uid: str, connection_id: str) -> dict[str, Any]:
        doc = await self._run(self._store.get, uid, connection_id)
        if doc is None:
            raise ConnectionNotFoundError()
        return doc

    async def _check(self, data: JiraConnectionInput) -> tuple[str, JiraAccount]:
        """Valida a credencial no Jira antes de guardar qualquer coisa (F04-RF-02, F04-RF-03)."""
        try:
            site = normalize_site_url(data.site_url)
        except InvalidSiteUrlError:
            raise InvalidSiteError() from None
        async with self._client_factory(
            site, data.email, data.api_token.get_secret_value()
        ) as jira:
            try:
                return site, await jira.myself()
            except JiraAuthError:
                raise InvalidCredentialsError() from None
            except JiraError:
                raise UnreachableError() from None

    async def _fields(self, data: JiraConnectionInput) -> dict[str, Any]:
        site, account = await self._check(data)
        token = data.api_token.get_secret_value()
        encrypted = await self._run(self._cipher.encrypt, token)
        return {
            "siteUrl": site,
            "email": data.email,
            "accountId": account.account_id,
            "accountName": account.display_name,
            "tokenHint": _hint(token),
            "tokenCiphertext": encrypted.ciphertext,
            "kmsKeyVersion": encrypted.key_version,
            "authType": "api_token",
            "status": "ok",
            "lastValidatedAt": self._clock(),
        }

    async def create(self, uid: str, data: JiraConnectionInput) -> JiraConnection:
        # MVP: uma conexão por usuário (o modelo aceita N). A checagem antes de validar evita
        # gastar uma chamada ao Jira; duas criações simultâneas são improváveis numa tela só.
        if await self._run(self._store.list, uid):
            raise ConnectionExistsError()
        fields = await self._fields(data)
        doc = {**fields, "createdAt": self._clock()}
        connection_id = await self._run(self._store.create, uid, doc)
        return _out({"id": connection_id, **doc})

    async def replace(
        self, uid: str, connection_id: str, data: JiraConnectionInput
    ) -> JiraConnection:
        current = await self._get(uid, connection_id)
        fields = await self._fields(data)
        await self._run(self._store.update, uid, connection_id, fields)
        return _out({**current, **fields})

    async def validate(self, uid: str, connection_id: str) -> JiraConnection:
        """Testa a credencial guardada; 401/403 marca a conexão como inválida (F04-RF-06)."""
        current = await self._get(uid, connection_id)
        async with await self.client_for(uid, connection_id, doc=current) as jira:
            try:
                account = await jira.myself()
            except JiraAuthError:
                return await self.mark_invalid(uid, connection_id, current)
            except JiraError:
                raise UnreachableError() from None
        fields = {
            "status": "ok",
            "accountName": account.display_name,
            "lastValidatedAt": self._clock(),
        }
        await self._run(self._store.update, uid, connection_id, fields)
        return _out({**current, **fields})

    async def mark_invalid(
        self, uid: str, connection_id: str, doc: dict[str, Any] | None = None
    ) -> JiraConnection:
        """Chamado quando o Jira recusa o token em qualquer uso (validação aqui; F05/F09 depois)."""
        current = doc or await self._get(uid, connection_id)
        await self._run(self._store.update, uid, connection_id, {"status": "invalid"})
        return _out({**current, "status": "invalid"})

    async def delete(self, uid: str, connection_id: str) -> None:
        await self._run(self._store.delete, uid, connection_id)

    async def client_for(
        self, uid: str, connection_id: str, *, doc: dict[str, Any] | None = None
    ) -> JiraClient:
        """Cliente Jira com o token decifrado só para esta requisição (F04-RT-05)."""
        current = doc or await self._get(uid, connection_id)
        token = await self._run(self._cipher.decrypt, current["tokenCiphertext"])
        return self._client_factory(current["siteUrl"], current["email"], token)
