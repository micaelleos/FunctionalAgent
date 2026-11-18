"""Confirmação humana das ações propostas pelo agente (F06, ADR-003, Constituição Art. IV).

A única porta de escrita no Jira. O agente só cria `pending_actions`; aqui, depois do clique do
usuário, a ação é executada **exatamente** como foi exibida:

- o hash do payload é conferido (F06-RT-02) e os campos do Jira são derivados dele, sem LLM
  (F06-RT-03, F06-RT-07);
- a transição `pending → executing` roda numa transação: confirmar duas vezes executa uma vez
  (F06-RT-01);
- escreve só na conexão e no site que estavam em uso quando a ação foi proposta.

Estados: `pending` → `executing` → `done` | `failed`; `pending` → `rejected` | `expired`. Uma falha
em que o Jira certamente não gravou (credencial, limite de requisições, site fora do ar) volta a
`pending`, para o usuário confirmar de novo; uma falha incerta (timeout depois de enviar) vira
`failed`, porque repetir poderia duplicar a issue.
"""

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, NoReturn, Protocol

from pydantic import BaseModel

from app.agent.spec.jira_payload import (
    jira_create_fields,
    jira_update_fields,
    payload_hash,
    resolve_issue_type,
)
from app.core.config import Settings
from app.core.errors import ApiProblemError
from app.core.logging import uid_hash
from app.core.telemetry import in_thread
from app.integrations.jira.client import (
    JiraAuthError,
    JiraBadRequestError,
    JiraClient,
    JiraError,
    JiraForbiddenError,
    JiraNotFoundError,
    JiraRateLimitedError,
    JiraUncertainError,
    JiraUnreachableError,
)
from app.repositories.actions import Decide, TransitionConflictError
from app.services.jira_connections import JiraConnectionService

log = logging.getLogger("app.actions")

# Uma execução dura no máximo o timeout do Jira (20 s); passado isto, o processo caiu no meio.
STALE_EXECUTION = timedelta(minutes=2)

ActionStatus = Literal["pending", "executing", "done", "failed", "rejected", "expired"]


class ActionStore(Protocol):
    def get_action(self, uid: str, action_id: str) -> dict[str, Any] | None: ...
    def list_actions(self, uid: str, conversation_id: str) -> list[dict[str, Any]]: ...
    def transition(self, uid: str, action_id: str, decide: Decide) -> dict[str, Any] | None: ...
    def update_action(self, uid: str, action_id: str, data: dict[str, Any]) -> None: ...
    def complete_action(
        self,
        uid: str,
        action_id: str,
        change: dict[str, Any],
        issue_key: str,
        issue: dict[str, Any],
        first_time: dict[str, Any],
    ) -> None: ...
    def add_system_message(self, uid: str, conversation_id: str, data: dict[str, Any]) -> str: ...


class ActionResult(BaseModel):
    issue_key: str
    url: str


def _issue_record(
    doc: dict[str, Any], result: ActionResult, now: datetime
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Registro de `users/{uid}/jira_issues/{key}` (F10): o que muda a cada ação e o que só
    entra na 1ª vez que o SpecFlow toca na issue."""
    payload, preview = doc["payload"], doc.get("preview") or {}
    issue: dict[str, Any] = {
        "url": result.url,
        "lastActionId": doc["id"],
        "conversationId": doc["conversationId"],
        "updatedAt": now,
    }
    if payload.get("spec") is not None:
        issue["specActionId"] = doc["id"]  # base do "Copiar para agente" (F10-RF-06)
    if "labels" in payload:
        issue["labels"] = list(payload.get("labels") or [])
    summary = preview.get("summary") or payload.get("summary")
    if summary:
        issue["summary"] = summary
    if doc["kind"] == "create_issue":
        issue |= {
            "projectKey": payload["project_key"],
            "issueType": payload["issue_type"],
            "actionId": doc["id"],
            "operation": "created",
            "createdAt": now,
        }
        return issue, {}
    if preview.get("issue_type"):
        issue["issueType"] = preview["issue_type"]
    first_time: dict[str, Any] = {
        "projectKey": result.issue_key.rsplit("-", 1)[0],
        "issueType": preview.get("issue_type") or "",
        "summary": summary or "",
        "labels": [],
        "operation": "updated",
        "createdAt": now,
    }
    return issue, first_time


class ActionError(BaseModel):
    code: str
    message: str


class ActionOut(BaseModel):
    """O cartão inteiro: o que vai ao Jira (`preview`), a prontidão e o estado (F06-RF-01)."""

    id: str
    kind: Literal["create_issue", "update_issue"]
    status: ActionStatus
    conversation_id: str
    preview: dict[str, Any]
    readiness: dict[str, Any]
    labels: list[str]
    created_at: datetime
    expires_at: datetime
    result: ActionResult | None = None
    error: ActionError | None = None


# ------------------------------------------------------------------------------ erros da API


class ActionNotFoundError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(404, "action-not-found", "Ação não encontrada")


class ActionExpiredError(ApiProblemError):
    def __init__(self, action: ActionOut) -> None:
        super().__init__(
            410,
            "action-expired",
            "Ação expirada",
            "A proposta expirou (24 h). Peça ao agente para propor de novo.",
            action=action.model_dump(mode="json"),
        )


class ActionNotPendingError(ApiProblemError):
    """409: já executada, recusada ou em execução; o corpo traz o estado atual e o resultado."""

    def __init__(self, action: ActionOut) -> None:
        super().__init__(
            409,
            "action-not-pending",
            "Ação já tratada",
            f"Esta ação já está {_STATUS_TEXT[action.status]}.",
            action=action.model_dump(mode="json"),
        )


class ActionFailedError(ApiProblemError):
    """422: o Jira recusou ou não respondeu; `detail` é a mensagem traduzida (F06-RF-07)."""

    def __init__(self, action: ActionOut, error: ActionError) -> None:
        super().__init__(
            422,
            error.code,
            "O Jira não executou a ação",
            error.message,
            action=action.model_dump(mode="json"),
        )


class ActionsDisabledError(ApiProblemError):
    def __init__(self) -> None:
        super().__init__(
            503,
            "actions-disabled",
            "Escritas no Jira desligadas",
            "As confirmações estão temporariamente desligadas. A proposta continua guardada.",
        )


_STATUS_TEXT: dict[str, str] = {
    "pending": "pendente",
    "executing": "em execução",
    "done": "concluída",
    "failed": "com falha",
    "rejected": "recusada",
    "expired": "expirada",
}


# ------------------------------------------------------------------------------ tradução


class Failure(BaseModel):
    code: str
    message: str
    retryable: bool  # o Jira certamente não gravou: a ação volta a `pending`


def translate(kind: str, payload: dict[str, Any], exc: JiraError) -> Failure:
    """Erro do Jira → mensagem em pt-BR para o usuário (F06-RF-07)."""
    creating = kind == "create_issue"
    where = (
        f"criar issues no projeto {payload.get('project_key')}"
        if creating
        else f"editar a issue {payload.get('issue_key')}"
    )
    forbidden = f"Você não tem permissão para {where}."
    if isinstance(exc, JiraForbiddenError):
        return Failure(code="jira-forbidden", message=forbidden, retryable=False)
    if isinstance(exc, JiraBadRequestError):
        if "permission" in str(exc).lower() or "permissão" in str(exc).lower():
            return Failure(code="jira-forbidden", message=forbidden, retryable=False)
        return Failure(code="jira-rejected", message=_rejected(payload, exc), retryable=False)
    if isinstance(exc, JiraNotFoundError):
        message = (
            f"O projeto {payload.get('project_key')} não foi encontrado no Jira."
            if creating
            else f"A issue {payload.get('issue_key')} não existe mais ou você não tem mais "
            "acesso a ela."
        )
        return Failure(code="jira-not-found", message=message, retryable=False)
    if isinstance(exc, JiraAuthError):
        return Failure(
            code="jira-auth",
            message="O Jira recusou a conexão. Reconecte em Configurações e confirme de novo.",
            retryable=True,
        )
    if isinstance(exc, JiraRateLimitedError):
        return Failure(
            code="jira-rate-limited",
            message="O Jira está limitando as requisições. Confirme de novo em alguns minutos.",
            retryable=True,
        )
    if isinstance(exc, JiraUncertainError):
        target = "a issue foi criada" if creating else "a issue foi atualizada"
        return Failure(
            code="jira-uncertain",
            message=f"O Jira não respondeu a tempo. Confira no Jira se {target} antes de pedir "
            "de novo.",
            retryable=False,
        )
    if isinstance(exc, JiraUnreachableError):
        return Failure(
            code="jira-unreachable",
            message="Não foi possível falar com o Jira agora. Confirme de novo em instantes.",
            retryable=True,
        )
    return Failure(code="jira-error", message=f"O Jira recusou a ação: {exc}", retryable=False)


def _rejected(payload: dict[str, Any], exc: JiraBadRequestError) -> str:
    fields = exc.errors
    if "priority" in fields and payload.get("priority"):
        return f'A prioridade "{payload.get("priority")}" não existe neste projeto do Jira.'
    if "parent" in fields:
        return (
            f"O pai {payload.get('parent_key')} não existe ou não pode ser pai deste tipo de issue."
        )
    if "issuetype" in fields:
        return (
            f'O tipo "{payload.get("issue_type")}" não existe no projeto '
            f"{payload.get('project_key')}."
        )
    if "labels" in fields:
        return f"O Jira recusou as labels: {fields['labels']}"
    custom = [k for k in fields if k.startswith("customfield_")]
    if custom:
        return (
            "O projeto exige campos que o SpecFlow não preenche "
            f"({'; '.join(fields[k] for k in custom)}). Ajuste o projeto no Jira ou crie a issue "
            "por lá."
        )
    return f"O Jira recusou a ação: {exc}"


# ------------------------------------------------------------------------------ serviço


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _expired(doc: dict[str, Any], now: datetime) -> bool:
    return doc["status"] == "pending" and _aware(doc["expiresAt"]) <= now


def to_out(doc: dict[str, Any], now: datetime) -> ActionOut:
    status = "expired" if _expired(doc, now) else doc["status"]
    return ActionOut(
        id=doc["id"],
        kind=doc["kind"],
        status=status,
        conversation_id=doc["conversationId"],
        preview=doc.get("preview") or {},
        readiness=doc.get("readiness") or {},
        labels=list(doc.get("labels") or []),
        created_at=doc["createdAt"],
        expires_at=doc["expiresAt"],
        result=ActionResult(**doc["result"]) if doc.get("result") else None,
        error=ActionError(**doc["error"]) if doc.get("error") else None,
    )


def describe(doc: dict[str, Any]) -> str:
    """Uma linha sobre a ação, para a mensagem de sistema e para o prompt do agente."""
    preview = doc.get("preview") or {}
    payload = doc.get("payload") or {}
    if doc["kind"] == "create_issue":
        return (
            f'criar {payload.get("issue_type", "issue")} "{preview.get("summary", "")}" '
            f"em {payload.get('project_key')}"
        )
    return f"atualizar {payload.get('issue_key')}"


class ActionService:
    def __init__(
        self,
        store: ActionStore,
        jira: JiraConnectionService,
        settings: Settings,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._store = store
        self._jira = jira
        self._settings = settings
        self._clock = clock

    async def _run[T](self, fn: Callable[..., T], *args: Any) -> T:
        return await in_thread(fn, *args)

    async def list(self, uid: str, conversation_id: str) -> list[ActionOut]:
        now = self._clock()
        docs = await self._run(self._store.list_actions, uid, conversation_id)
        return [to_out(d, now) for d in docs]

    async def reject(self, uid: str, action_id: str) -> ActionOut:
        now = self._clock()
        claim = uuid.uuid4().hex

        def decide(doc: dict[str, Any] | None) -> dict[str, Any] | None:
            if doc is None or doc["status"] != "pending":
                return None
            if _expired(doc, now):
                return {"status": "expired"}
            return {"status": "rejected", "claim": claim, "decidedAt": now}

        doc = await self._transition(uid, action_id, decide)
        if doc is None:
            raise ActionNotFoundError()
        out = to_out(doc, now)
        if out.status == "expired":
            raise ActionExpiredError(out)
        if doc.get("claim") != claim:
            raise ActionNotPendingError(out)
        await self._system_message(uid, doc, f"O usuário recusou a ação: {describe(doc)}.")
        self._audit(uid, doc, "rejected")
        return out

    async def confirm(self, uid: str, action_id: str) -> ActionOut:
        if not self._settings.actions_enabled:
            raise ActionsDisabledError()
        now = self._clock()
        claim = uuid.uuid4().hex

        def decide(doc: dict[str, Any] | None) -> dict[str, Any] | None:
            if doc is None:
                return None
            if _expired(doc, now):
                return {"status": "expired"}
            if doc["status"] == "pending":
                return {"status": "executing", "claim": claim, "executingAt": now}
            if doc["status"] == "executing" and _aware(doc["executingAt"]) + STALE_EXECUTION < now:
                # O processo caiu no meio: não dá para saber se o Jira gravou.
                failure = translate(doc["kind"], doc["payload"], JiraUncertainError("interrompida"))
                return {"status": "failed", "error": _error(failure).model_dump()}
            return None

        doc = await self._transition(uid, action_id, decide)
        if doc is None:
            raise ActionNotFoundError()
        if doc["status"] == "expired":
            raise ActionExpiredError(to_out(doc, now))
        if doc.get("claim") != claim or doc["status"] != "executing":
            raise ActionNotPendingError(to_out(doc, now))
        return await self._execute(uid, doc, now)

    async def _transition(self, uid: str, action_id: str, decide: Decide) -> dict[str, Any] | None:
        try:
            return await self._run(self._store.transition, uid, action_id, decide)
        except TransitionConflictError:
            # Outra confirmação/recusa venceu a disputa: responde com o estado atual (409).
            current = await self._run(self._store.get_action, uid, action_id)
            if current is None:
                raise ActionNotFoundError() from None
            raise ActionNotPendingError(to_out(current, self._clock())) from None

    async def _execute(self, uid: str, doc: dict[str, Any], now: datetime) -> ActionOut:
        payload: dict[str, Any] = doc["payload"]
        if payload_hash(payload) != doc.get("payloadHash"):
            # O payload mudou depois de exibido: nunca executar (F06-RT-02).
            failure = Failure(
                code="action-integrity",
                message="A proposta foi alterada depois de exibida e não será executada. "
                "Peça ao agente para propor de novo.",
                retryable=False,
            )
            await self._fail(uid, doc, failure, now)
        try:
            client = await self._client(uid, doc)
        except _ConnectionChangedError:
            failure = Failure(
                code="jira-connection-changed",
                message="A conexão com o Jira mudou desde a proposta. Peça ao agente para propor "
                "de novo.",
                retryable=False,
            )
            await self._fail(uid, doc, failure, now)
        try:
            result = await self._write(client, doc["kind"], payload)
        except _IssueTypeMissingError as exc:
            failure = Failure(code="jira-issue-type", message=str(exc), retryable=False)
            await self._fail(uid, doc, failure, now)
        except JiraError as exc:
            failure = translate(doc["kind"], payload, exc)
            if isinstance(exc, JiraAuthError) and doc.get("connectionId"):
                await self._jira.mark_invalid(uid, doc["connectionId"])
            await self._fail(uid, doc, failure, now)
        finally:
            await client.aclose()
        return await self._done(uid, doc, result, now)

    async def _client(self, uid: str, doc: dict[str, Any]) -> JiraClient:
        connections = {c.id: c for c in await self._jira.list(uid)}
        connection = connections.get(str(doc.get("connectionId")))
        if connection is None or connection.site_url != doc.get("siteUrl"):
            raise _ConnectionChangedError()
        return await self._jira.client_for(uid, connection.id)

    async def _write(self, client: JiraClient, kind: str, payload: dict[str, Any]) -> ActionResult:
        if kind == "create_issue":
            fields = jira_create_fields(payload)
            fields["issuetype"] = {"id": await self._issue_type_id(client, payload)}
            created = await client.create_issue(fields)
            return ActionResult(issue_key=created.key, url=created.url)
        key = str(payload["issue_key"])
        await client.update_issue(key, jira_update_fields(payload))
        return ActionResult(issue_key=key, url=f"{client.site_url}/browse/{key}")

    async def _issue_type_id(self, client: JiraClient, payload: dict[str, Any]) -> str:
        """O tipo vai pelo id do projeto: os nomes mudam com o idioma do site (ex.: "História")."""
        types = await client.project_issue_types(payload["project_key"])
        available = [(t.id, t.name, t.hierarchy_level) for t in types if not t.subtask]
        type_id = resolve_issue_type(payload["issue_type"], available)
        if type_id is None:
            names = ", ".join(t.name for t in types if not t.subtask) or "nenhum"
            raise _IssueTypeMissingError(
                f"O projeto {payload['project_key']} não tem um tipo equivalente a "
                f'"{payload["issue_type"]}" (tipos do projeto: {names}).'
            )
        return type_id

    async def _done(
        self, uid: str, doc: dict[str, Any], result: ActionResult, now: datetime
    ) -> ActionOut:
        executed_at = self._clock()
        change = {"status": "done", "result": result.model_dump(), "executedAt": executed_at}
        issue, first_time = _issue_record(doc, result, executed_at)
        # Ação concluída e histórico (F10) na mesma transação (F10-RT-01).
        await self._run(
            self._store.complete_action, uid, doc["id"], change, result.issue_key, issue, first_time
        )
        doc = {**doc, **change}
        verb = "criou" if doc["kind"] == "create_issue" else "atualizou"
        text = f"O usuário confirmou e o SpecFlow {verb} {result.issue_key} ({result.url})."
        await self._system_message(uid, doc, text)
        self._audit(uid, doc, "done", issue_key=result.issue_key)
        return to_out(doc, now)

    async def _fail(
        self, uid: str, doc: dict[str, Any], failure: Failure, now: datetime
    ) -> NoReturn:
        error = _error(failure)
        status = "pending" if failure.retryable else "failed"
        change = {"status": status, "error": error.model_dump(), "claim": None}
        await self._run(self._store.update_action, uid, doc["id"], change)
        doc = {**doc, **change}
        if not failure.retryable:
            await self._system_message(
                uid, doc, f"A ação ({describe(doc)}) falhou no Jira: {failure.message}"
            )
        self._audit(uid, doc, status, code=failure.code)
        raise ActionFailedError(to_out(doc, now), error)

    async def _system_message(self, uid: str, doc: dict[str, Any], text: str) -> None:
        message = {"content": text, "actionId": doc["id"], "createdAt": self._clock()}
        await self._run(self._store.add_system_message, uid, doc["conversationId"], message)

    def _audit(self, uid: str, doc: dict[str, Any], result: str, **extra: Any) -> None:
        """Auditoria `jira_write` (F06-RT-06): toda decisão sobre uma ação, sem conteúdo."""
        log.info(
            "jira_write",
            extra={
                "fields": {
                    "event": "jira_write",
                    "uid_hash": uid_hash(uid),
                    "action_id": doc["id"],
                    "kind": doc["kind"],
                    "result": result,
                    "issue_key": extra.get("issue_key"),
                    "code": extra.get("code"),
                }
            },
        )


class _ConnectionChangedError(Exception):
    pass


class _IssueTypeMissingError(Exception):
    pass


def _error(failure: Failure) -> ActionError:
    return ActionError(code=failure.code, message=failure.message)
