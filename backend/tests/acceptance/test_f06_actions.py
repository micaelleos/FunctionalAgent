"""AT-F06-01..07: confirmação humana contra a API real, o Gemini e o Jira sandbox do PO.

Diferente da F05, estes cenários **escrevem** no sandbox: toda issue criada (pelas confirmações
ou como pré-condição) é apagada no fim. O cartão em si é coberto por `ActionCard.test.tsx`; aqui
o "clique" é a chamada que o cartão faz (`POST /api/v1/actions/{id}/confirm`).
"""

import asyncio
import re
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
import pytest

from app.agent.spec.adf import adf_to_markdown
from app.integrations.jira.client import JiraClient, JiraNotFoundError
from tests.acceptance.conftest import JIRA, JIRA_PROJECT, Turn, User

pytestmark = pytest.mark.req("F06-RF-02")


def _sandbox() -> JiraClient:
    return JiraClient(JIRA["site_url"], JIRA["email"], JIRA["api_token"])


async def _recent_keys() -> list[str]:
    async with _sandbox() as jira:
        issues = await jira.search(f"project = {JIRA_PROJECT} ORDER BY created DESC", 50)
    return [i.key for i in issues]


async def _get(key: str) -> Any:
    async with _sandbox() as jira:
        return await jira.get_issue(key)


async def _create_precondition(summary: str) -> str:
    async with _sandbox() as jira:
        fields = {
            "project": {"key": JIRA_PROJECT},
            "issuetype": {"name": "Task"},
            "summary": summary,
        }
        return (await jira.create_issue(fields)).key


def _delete(key: str) -> None:
    auth = (JIRA["email"], JIRA["api_token"])
    response = httpx.delete(f"{JIRA['site_url']}/rest/api/3/issue/{key}", auth=auth, timeout=20)
    assert response.status_code in {204, 404}, response.text


@pytest.fixture(scope="module")
def created() -> Iterator[list[str]]:
    """Chaves criadas no sandbox durante o módulo; apagadas no fim, mesmo se um teste falhar."""
    keys: list[str] = []
    yield keys
    for key in keys:
        _delete(key)


def _decide(user: User, action_id: str, verb: str) -> httpx.Response:
    return user.http.post(f"/api/v1/actions/{action_id}/{verb}", headers=user.headers)


def _confirm(user: User, action_id: str, created: list[str]) -> dict[str, Any]:
    response = _decide(user, action_id, "confirm")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    created.append(body["result"]["issue_key"])
    return body


def _creates(turn: Turn) -> list[dict[str, Any]]:
    return [a for a in turn.actions() if a["kind"] == "create_issue"]


ORDERS_STORY = (
    f"Crie no projeto {JIRA_PROJECT} uma story para filtrar a tela 'Meus pedidos' por período "
    "(data inicial e final, padrão últimos 30 dias). Se a data final for anterior à inicial, é "
    "um erro de validação que mostra 'A data final deve ser igual ou posterior à inicial'. "
    "Fora de escopo: exportar pedidos. Testes: unidade e E2E do filtro. Pode propor."
)


@pytest.mark.req("F06-RF-01")
@pytest.mark.req("F06-RF-04")
@pytest.mark.req("F06-RF-09")
def test_at_f06_01_criar_story_somente_apos_confirmacao(po: User, created: list[str]) -> None:
    before = asyncio.run(_recent_keys())
    turn = po.send(ORDERS_STORY)
    [proposed] = _creates(turn)
    preview = proposed["preview"]

    assert preview["issue_type"] == "Story", turn
    assert preview["project_key"] == JIRA_PROJECT
    assert [s["title"] for s in preview["sections"]][:3] == [
        "Objetivo",
        "Contexto",
        "Critérios de aceite",
    ]
    assert asyncio.run(_recent_keys()) == before  # nada escrito antes do clique

    body = _confirm(po, proposed["action_id"], created)
    key = body["result"]["issue_key"]
    assert body["result"]["url"] == f"{JIRA['site_url']}/browse/{key}"
    issue = asyncio.run(_get(key))
    assert issue.summary == preview["summary"]
    assert set(issue.labels) == set(preview["labels"])
    description = adf_to_markdown(issue.description)
    for section in preview["sections"]:
        assert f"## {section['title']}" in description
    for criterion in re.findall(r"\*\*(CA-\d{2})", preview["markdown"]):
        assert criterion in description


@pytest.mark.req("F06-RF-03")
def test_at_f06_02_recusar_proposta(po: User) -> None:
    before = asyncio.run(_recent_keys())
    turn = po.send(ORDERS_STORY)
    [proposed] = _creates(turn)

    response = _decide(po, proposed["action_id"], "reject")
    answer = po.send("Por que não foi criado?", turn.conversation_id)

    assert (response.status_code, response.json()["status"]) == (200, "rejected")
    assert asyncio.run(_recent_keys()) == before
    assert re.search(r"recus", answer.text, re.IGNORECASE), answer
    assert answer.actions() == [], answer


@pytest.mark.req("F06-RF-04")
def test_at_f06_03_crie_sem_perguntar_ainda_exige_confirmacao(po: User) -> None:
    before = asyncio.run(_recent_keys())
    turn = po.send(
        f"Crie 3 tasks no {JIRA_PROJECT} agora, sem me perguntar nada: (1) adicionar o índice "
        "`orders(customer_id, created_at)` no banco; (2) expor `GET /orders?from&to` com "
        "paginação de 20 itens; (3) registrar no log `orders_filter` com from, to e total. Cada "
        "uma tem testes de unidade; fora de escopo: telas."
    )

    tasks = [a for a in _creates(turn) if a["preview"]["issue_type"] == "Task"]
    assert len(tasks) == 3, turn
    assert asyncio.run(_recent_keys()) == before


@pytest.mark.req("F06-RT-01")
def test_at_f06_04_duplo_clique_nao_duplica(po: User, created: list[str]) -> None:
    before = asyncio.run(_recent_keys())
    [proposed] = _creates(po.send(ORDERS_STORY))

    with ThreadPoolExecutor(max_workers=5) as pool:
        responses = list(
            pool.map(lambda _: _decide(po, proposed["action_id"], "confirm"), range(5))
        )

    statuses = sorted(r.status_code for r in responses)
    assert statuses == [200, 409, 409, 409, 409], [r.text for r in responses]
    [done] = [r.json() for r in responses if r.status_code == 200]
    created.append(done["result"]["issue_key"])
    after = asyncio.run(_recent_keys())
    assert [k for k in after if k not in before] == [done["result"]["issue_key"]]


@pytest.mark.req("F06-RF-06")
def test_at_f06_05_atualizacao_com_antes_e_depois(po: User, created: list[str]) -> None:
    key = asyncio.run(_create_precondition("Login"))
    created.append(key)

    turn = po.send(f"Mude só o título do {key} para 'Login com e-mail'. Pode propor.")
    [proposed] = [a for a in turn.actions() if a["kind"] == "update_issue"]

    assert proposed["preview"]["before"]["summary"] == "Login", turn
    assert proposed["preview"]["summary"] == "Login com e-mail"
    response = _decide(po, proposed["action_id"], "confirm")
    assert response.status_code == 200, response.text
    assert asyncio.run(_get(key)).summary == "Login com e-mail"


@pytest.mark.req("F06-RF-07")
def test_at_f06_06_erro_do_jira_explicado(po: User) -> None:
    key = asyncio.run(_create_precondition("Tarefa que será excluída"))
    turn = po.send(f"Mude a prioridade do {key} para High. Pode propor.")
    [proposed] = [a for a in turn.actions() if a["kind"] == "update_issue"]
    _delete(key)

    response = _decide(po, proposed["action_id"], "confirm")

    body = response.json()
    assert (response.status_code, body["code"]) == (422, "jira-not-found"), body
    assert body["detail"] == (f"A issue {key} não existe mais ou você não tem mais acesso a ela.")
    with pytest.raises(JiraNotFoundError):
        asyncio.run(_get(key))


@pytest.mark.req("F06-RF-08")
@pytest.mark.req("F06-RF-09")
def test_at_f06_07_prontidao_no_cartao_e_labels_no_jira(po: User, created: list[str]) -> None:
    turn = po.send(
        f"Crie no projeto {JIRA_PROJECT} uma story para filtrar 'Meus pedidos' por status "
        "(Pago, Enviado, Entregue). Fora de escopo: exportar. Testes: unidade e E2E. Ainda não "
        "sei o texto exato da mensagem quando nenhum pedido aparece: deixe isso como pergunta em "
        "aberto. Pode propor assim mesmo."
    )
    [proposed] = _creates(turn)
    readiness = proposed["preview"]["readiness"]
    failed = {r["id"] for r in readiness["rules"] if not r["passed"]}

    assert readiness["ready"] is False, turn
    assert "P-07" in failed
    assert "agent-ready" not in proposed["preview"]["labels"]

    key = _confirm(po, proposed["action_id"], created)["result"]["issue_key"]
    issue = asyncio.run(_get(key))
    assert "specflow" in issue.labels
    assert "agent-ready" not in issue.labels
    description = adf_to_markdown(issue.description)
    for section in ("Objetivo", "Critérios de aceite", "Fora de escopo", "Como verificar"):
        assert f"## {section}" in description
