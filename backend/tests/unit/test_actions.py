"""Confirmação humana das ações propostas (F06): execução exata, única e só depois do clique."""

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any, cast

import httpx
import pytest

from app.agent.spec.adf import adf_to_markdown
from app.agent.spec.jira_payload import (
    create_payload,
    jira_create_fields,
    payload_hash,
    update_payload,
)
from app.core.config import Settings
from app.core.errors import ApiProblemError
from app.core.logging import uid_hash
from app.services.actions import ActionService, translate
from app.services.chat import ACTION_TTL
from app.services.jira_connections import JiraConnectionService
from tests.chat_fakes import (
    ISSUE_TYPES_EN,
    NOW,
    SITE,
    FakeJiraService,
    MemoryChatStore,
    issue_types_response,
)
from tests.spec_fixtures import pix_story

pytestmark = pytest.mark.req("F06-RF-02")

UID, OTHER = "alice", "bob"


class FakeJira:
    """Jira com escritas: cria ABC-<n>, aceita PUT e responde o que o teste mandar."""

    def __init__(
        self, *responses: httpx.Response | Exception, types: list[dict[str, Any]] | None = None
    ) -> None:
        self.responses = list(responses)
        self.writes: list[httpx.Request] = []
        self.types = ISSUE_TYPES_EN if types is None else types

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if (types := issue_types_response(request, self.types)) is not None:
            return types
        assert request.method in {"POST", "PUT"}, request
        self.writes.append(request)
        if self.responses:
            reply = self.responses.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply
        if request.method == "POST":
            return httpx.Response(201, json={"id": "1", "key": f"ABC-{len(self.writes)}"})
        return httpx.Response(204)

    def bodies(self) -> list[dict[str, Any]]:
        return [json.loads(r.content) for r in self.writes]


def _setup(
    jira: FakeJira | None = None, *, settings: Settings | None = None
) -> tuple[ActionService, MemoryChatStore, FakeJiraService, FakeJira]:
    fake = jira or FakeJira()
    store = MemoryChatStore()
    service_jira = FakeJiraService(handler=fake)
    store.conversations[UID] = {"conv-1": {"messageCount": 2}}
    service = ActionService(
        store,
        cast(JiraConnectionService, service_jira),
        settings or Settings(env="test"),
        clock=lambda: NOW,
    )
    return service, store, service_jira, fake


def _propose(
    store: MemoryChatStore,
    payload: dict[str, Any] | None = None,
    *,
    kind: str = "create_issue",
    uid: str = UID,
    **extra: Any,
) -> str:
    payload = payload or create_payload(pix_story(), "ABC", ["agent-ready", "specflow"], None)
    doc = {
        "kind": kind,
        "payload": payload,
        "payloadHash": payload_hash(payload),
        "readiness": {"ready": True},
        "labels": payload.get("labels", []),
        "preview": {"summary": pix_story().title},
        "status": "pending",
        "conversationId": "conv-1",
        "connectionId": "conn-1",
        "siteUrl": SITE,
        "createdAt": NOW - timedelta(minutes=5),
        "expiresAt": NOW - timedelta(minutes=5) + ACTION_TTL,
    } | extra
    return store.create_action(uid, doc)


def _system_messages(store: MemoryChatStore) -> list[str]:
    return [m["content"] for m in store.messages.get((UID, "conv-1"), []) if m["role"] == "system"]


async def _problem(coro: Any) -> ApiProblemError:
    with pytest.raises(ApiProblemError) as info:
        await coro
    return info.value


# ------------------------------------------------------------------------------ confirmar


@pytest.mark.req("F06-RF-09")
@pytest.mark.req("F06-RT-07")
async def test_confirmar_cria_exatamente_o_que_foi_exibido() -> None:
    service, store, _, fake = _setup()
    aid = _propose(store)
    payload = store.get_action(UID, aid)["payload"]  # type: ignore[index]

    out = await service.confirm(UID, aid)

    [body] = fake.bodies()
    assert body == {"fields": jira_create_fields(payload) | {"issuetype": {"id": "10004"}}}
    assert body["fields"]["labels"] == ["agent-ready", "specflow"]
    description = adf_to_markdown(body["fields"]["description"])
    for section in ("Objetivo", "Critérios de aceite", "Fora de escopo", "Como verificar"):
        assert f"## {section}" in description
    assert out.status == "done"
    assert out.result is not None
    assert (out.result.issue_key, out.result.url) == ("ABC-1", f"{SITE}/browse/ABC-1")


@pytest.mark.req("F06-RF-03")
async def test_confirmar_grava_issue_e_mensagem_de_sistema() -> None:
    service, store, _, _ = _setup()
    aid = _propose(store)

    await service.confirm(UID, aid)

    issue = store.issues[UID]["ABC-1"]
    assert issue["projectKey"] == "ABC"
    assert issue["issueType"] == "Story"
    assert issue["actionId"] == aid
    assert issue["conversationId"] == "conv-1"
    assert _system_messages(store) == [
        f"O usuário confirmou e o SpecFlow criou ABC-1 ({SITE}/browse/ABC-1)."
    ]


async def test_prioridade_vai_ao_jira_so_quando_proposta() -> None:
    service, store, _, fake = _setup()
    with_priority = create_payload(pix_story(), "ABC", ["specflow"], None, "High")

    await service.confirm(UID, _propose(store, with_priority))
    await service.confirm(UID, _propose(store))

    first, second = fake.bodies()
    assert first["fields"]["priority"] == {"name": "High"}
    assert "priority" not in second["fields"]


@pytest.mark.req("F06-RF-06")
async def test_atualizacao_so_envia_os_campos_permitidos() -> None:
    service, store, _, fake = _setup()
    payload = update_payload("ABC-7", None, "Low", ["specflow", "time-a"])

    out = await service.confirm(UID, _propose(store, payload, kind="update_issue"))

    [request] = fake.writes
    assert (request.method, request.url.path) == ("PUT", "/rest/api/3/issue/ABC-7")
    assert json.loads(request.content) == {
        "fields": {"priority": {"name": "Low"}, "labels": ["specflow", "time-a"]}
    }
    assert out.result is not None
    assert out.result.issue_key == "ABC-7"
    # F10: a atualização também entra no histórico, marcada como só atualizada.
    record = store.issues[UID]["ABC-7"]
    assert (record["operation"], record["projectKey"], record["labels"]) == (
        "updated",
        "ABC",
        ["specflow", "time-a"],
    )
    assert "specActionId" not in record  # sem spec: nada para copiar ao agente


@pytest.mark.req("F06-RT-01")
async def test_dez_confirmacoes_paralelas_criam_uma_issue() -> None:
    service, store, _, fake = _setup()
    aid = _propose(store)

    results = await asyncio.gather(
        *(service.confirm(UID, aid) for _ in range(10)), return_exceptions=True
    )

    assert len(fake.writes) == 1
    done = [r for r in results if not isinstance(r, BaseException)]
    conflicts = [r for r in results if isinstance(r, ApiProblemError)]
    assert len(done) == 1
    assert len(conflicts) == 9
    assert {c.status for c in conflicts} == {409}


async def test_confirmar_de_novo_devolve_409_com_o_resultado() -> None:
    service, store, _, fake = _setup()
    aid = _propose(store)
    await service.confirm(UID, aid)

    problem = await _problem(service.confirm(UID, aid))

    assert (problem.status, problem.code) == (409, "action-not-pending")
    assert problem.extra["action"]["result"]["issue_key"] == "ABC-1"
    assert len(fake.writes) == 1


@pytest.mark.req("F06-RT-02")
async def test_payload_alterado_depois_de_exibido_nao_executa() -> None:
    service, store, _, fake = _setup()
    aid = _propose(store)
    store._action(UID, aid)["payload"]["project_key"] = "XYZ"  # type: ignore[index]

    problem = await _problem(service.confirm(UID, aid))

    assert (problem.status, problem.code) == (422, "action-integrity")
    assert fake.writes == []
    assert store.get_action(UID, aid)["status"] == "failed"  # type: ignore[index]


@pytest.mark.req("F06-RT-04")
async def test_acao_de_outro_usuario_e_404() -> None:
    service, store, _, fake = _setup()
    aid = _propose(store, uid=OTHER)

    for call in (service.confirm, service.reject):
        problem = await _problem(call(UID, aid))
        assert (problem.status, problem.code) == (404, "action-not-found")
    assert fake.writes == []
    assert await service.list(UID, "conv-1") == []


async def test_conexao_trocada_depois_da_proposta_nao_escreve() -> None:
    service, store, _, fake = _setup()
    aid = _propose(store, siteUrl="https://outro-site.atlassian.net")

    problem = await _problem(service.confirm(UID, aid))

    assert problem.code == "jira-connection-changed"
    assert fake.writes == []


async def test_escritas_desligadas_mantem_a_proposta() -> None:
    service, store, _, fake = _setup(settings=Settings(env="test", actions_enabled=False))
    aid = _propose(store)

    problem = await _problem(service.confirm(UID, aid))

    assert (problem.status, problem.code) == (503, "actions-disabled")
    assert store.get_action(UID, aid)["status"] == "pending"  # type: ignore[index]
    assert fake.writes == []


async def test_execucao_interrompida_vira_falha_incerta() -> None:
    service, store, _, fake = _setup()
    aid = _propose(store, status="executing", executingAt=NOW - timedelta(minutes=10))

    problem = await _problem(service.confirm(UID, aid))

    assert problem.code == "action-not-pending"
    assert problem.extra["action"]["status"] == "failed"
    assert problem.extra["action"]["error"]["code"] == "jira-uncertain"
    assert fake.writes == []


# ------------------------------------------------------------------------------ recusar e expirar


@pytest.mark.req("F06-RF-03")
async def test_recusar_nao_escreve_e_avisa_na_conversa() -> None:
    service, store, _, fake = _setup()
    aid = _propose(store)

    out = await service.reject(UID, aid)
    again = await _problem(service.reject(UID, aid))
    confirm = await _problem(service.confirm(UID, aid))

    assert out.status == "rejected"
    assert again.status == confirm.status == 409
    assert fake.writes == []
    assert _system_messages(store) == [
        'O usuário recusou a ação: criar Story "Permitir pagamento com Pix no checkout da loja" '
        "em ABC."
    ]


@pytest.mark.req("F06-RF-05")
@pytest.mark.req("F06-RT-05")
async def test_acao_expirada_responde_410_e_aparece_expirada() -> None:
    service, store, _, fake = _setup()
    aid = _propose(store, expiresAt=NOW - timedelta(seconds=1))

    [listed] = await service.list(UID, "conv-1")
    confirm = await _problem(service.confirm(UID, aid))
    reject = await _problem(service.reject(UID, aid))

    assert listed.status == "expired"
    assert (confirm.status, confirm.code) == (410, "action-expired")
    assert reject.status == 410
    assert fake.writes == []


# ------------------------------------------------------------------------------ erros do Jira


def _jira_error(status: int, body: dict[str, Any] | None = None) -> httpx.Response:
    return httpx.Response(status, json=body or {})


@pytest.mark.req("F06-RF-07")
@pytest.mark.parametrize(
    ("reply", "code", "message", "status"),
    [
        (
            _jira_error(403),
            "jira-forbidden",
            "Você não tem permissão para criar issues no projeto ABC.",
            "failed",
        ),
        (
            _jira_error(
                400, {"errors": {"project": "You do not have permission to create issues."}}
            ),
            "jira-forbidden",
            "Você não tem permissão para criar issues no projeto ABC.",
            "failed",
        ),
        (
            _jira_error(400, {"errors": {"priority": "Priority name 'Urgente' is not valid"}}),
            "jira-rejected",
            'A prioridade "Urgente" não existe neste projeto do Jira.',
            "failed",
        ),
        (
            _jira_error(400, {"errors": {"customfield_10020": "Team is required."}}),
            "jira-rejected",
            "O projeto exige campos que o SpecFlow não preenche (Team is required.). Ajuste o "
            "projeto no Jira ou crie a issue por lá.",
            "failed",
        ),
        (
            _jira_error(500),
            "jira-uncertain",
            "O Jira não respondeu a tempo. Confira no Jira se a issue foi criada antes de pedir "
            "de novo.",
            "failed",
        ),
        (
            httpx.ReadTimeout("lento"),
            "jira-uncertain",
            "O Jira não respondeu a tempo. Confira no Jira se a issue foi criada antes de pedir "
            "de novo.",
            "failed",
        ),
        (
            httpx.ConnectError("fora"),
            "jira-unreachable",
            "Não foi possível falar com o Jira agora. Confirme de novo em instantes.",
            "pending",
        ),
    ],
)
async def test_erro_do_jira_traduzido(
    reply: httpx.Response | Exception, code: str, message: str, status: str
) -> None:
    service, store, _, fake = _setup(FakeJira(reply))
    aid = _propose(store, create_payload(pix_story(), "ABC", ["specflow"], None, "Urgente"))

    problem = await _problem(service.confirm(UID, aid))

    assert (problem.status, problem.code, problem.detail) == (422, code, message)
    assert store.get_action(UID, aid)["status"] == status  # type: ignore[index]
    assert len(fake.writes) == 1  # escrita nunca é repetida depois de enviada


@pytest.mark.req("F06-RF-07")
async def test_issue_removida_antes_da_confirmacao() -> None:
    service, store, _, _ = _setup(FakeJira(_jira_error(404)))
    aid = _propose(store, update_payload("ABC-7", None, "Low", None), kind="update_issue")

    problem = await _problem(service.confirm(UID, aid))

    assert problem.detail == "A issue ABC-7 não existe mais ou você não tem mais acesso a ela."
    assert _system_messages(store) == [f"A ação (atualizar ABC-7) falhou no Jira: {problem.detail}"]


async def test_token_recusado_invalida_conexao_e_permite_confirmar_de_novo() -> None:
    service, store, jira, fake = _setup(FakeJira(_jira_error(401)))
    aid = _propose(store)

    problem = await _problem(service.confirm(UID, aid))
    out = await service.confirm(UID, aid)  # depois de reconectar

    assert problem.code == "jira-auth"
    assert jira.invalidated == ["conn-1"]
    assert out.status == "done"
    assert len(fake.writes) == 2


async def test_limite_de_requisicoes_repete_e_depois_devolve_a_proposta() -> None:
    limited = [_jira_error(429) for _ in range(3)]
    service, store, _, fake = _setup(FakeJira(*limited))
    aid = _propose(store)

    problem = await _problem(service.confirm(UID, aid))

    assert problem.code == "jira-rate-limited"
    assert len(fake.writes) == 3  # 429: o Jira não processou, então é seguro repetir
    assert store.get_action(UID, aid)["status"] == "pending"  # type: ignore[index]


def test_traducao_para_atualizacao_sem_permissao() -> None:
    from app.integrations.jira.client import JiraForbiddenError

    failure = translate("update_issue", {"issue_key": "ABC-7"}, JiraForbiddenError("403"))
    assert failure.message == "Você não tem permissão para editar a issue ABC-7."


# ------------------------------------------------------------------------------ auditoria


@pytest.mark.req("F06-RT-06")
async def test_auditoria_jira_write(caplog: pytest.LogCaptureFixture) -> None:
    service, store, _, _ = _setup(FakeJira(_jira_error(403)))
    created, refused = _propose(store), _propose(store)
    caplog.set_level(logging.INFO, logger="app.actions")

    await _problem(service.confirm(UID, created))
    await service.reject(UID, refused)

    events = [cast(Any, r).fields for r in caplog.records]
    assert events == [
        {
            "event": "jira_write",
            "uid_hash": uid_hash(UID),
            "action_id": created,
            "kind": "create_issue",
            "result": "failed",
            "issue_key": None,
            "code": "jira-forbidden",
        },
        {
            "event": "jira_write",
            "uid_hash": uid_hash(UID),
            "action_id": refused,
            "kind": "create_issue",
            "result": "rejected",
            "issue_key": None,
            "code": None,
        },
    ]


@pytest.mark.req("F06-RT-01")
async def test_disputa_perdida_na_transacao_responde_409_com_o_estado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.repositories.actions import TransitionConflictError

    service, store, _, fake = _setup()
    aid = _propose(store, status="executing", executingAt=NOW)

    def contention(*_: Any) -> None:
        raise TransitionConflictError(aid)

    monkeypatch.setattr(store, "transition", contention)

    problem = await _problem(service.confirm(UID, aid))

    assert (problem.status, problem.extra["action"]["status"]) == (409, "executing")
    assert fake.writes == []


ISSUE_TYPES_PT = [
    {"id": "20001", "name": "Epic", "hierarchyLevel": 1, "subtask": False},
    {"id": "20002", "name": "Subtarefa", "hierarchyLevel": -1, "subtask": True},
    {"id": "20003", "name": "Tarefa", "hierarchyLevel": 0, "subtask": False},
    {"id": "20004", "name": "História", "hierarchyLevel": 0, "subtask": False},
]


@pytest.mark.req("F06-RF-02")
@pytest.mark.parametrize(
    ("issue_type", "expected"), [("Story", "20004"), ("Task", "20003"), ("Epic", "20001")]
)
async def test_tipo_resolvido_pelo_id_em_site_em_portugues(issue_type: str, expected: str) -> None:
    service, store, _, fake = _setup(FakeJira(types=ISSUE_TYPES_PT))
    payload = create_payload(pix_story(), "ABC", ["specflow"], None) | {"issue_type": issue_type}
    aid = _propose(store, payload)

    await service.confirm(UID, aid)

    assert fake.bodies()[0]["fields"]["issuetype"] == {"id": expected}


@pytest.mark.req("F06-RF-07")
async def test_projeto_sem_tipo_equivalente_explica_os_tipos_disponiveis() -> None:
    only_tasks = [{"id": "1", "name": "Tarefa", "hierarchyLevel": 0, "subtask": False}]
    service, store, _, fake = _setup(FakeJira(types=only_tasks))
    aid = _propose(store)

    problem = await _problem(service.confirm(UID, aid))

    assert (problem.status, problem.code) == (422, "jira-issue-type")
    assert problem.detail == (
        'O projeto ABC não tem um tipo equivalente a "Story" (tipos do projeto: Tarefa).'
    )
    assert fake.writes == []
