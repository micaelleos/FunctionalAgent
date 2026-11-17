"""AT-F07-01..05: conversas persistentes contra a API real, o Gemini e o Jira sandbox do PO.

A tela (sidebar, histórico) é da F08, que repete estes cenários no navegador; aqui o "abrir a
conversa" é a chamada que a tela faz. O AT-F07-04 cria uma issue no sandbox (apagada no fim, salvo
com `ACCEPTANCE_KEEP_ISSUES=1`).
"""

import asyncio
import os
import re
from collections.abc import Iterator
from typing import Any

import pytest

from tests.acceptance.conftest import JIRA_PROJECT, User, new_user
from tests.acceptance.test_f06_actions import ORDERS_STORY, _creates, _delete, _get

pytestmark = pytest.mark.req("F07-RF-01")
BASE = "/api/v1/conversations"


@pytest.fixture(scope="module")
def owner() -> User:
    """Usuário novo para o módulo: a lista de conversas começa vazia."""
    return new_user(with_jira=True)


@pytest.fixture(scope="module")
def created() -> Iterator[list[str]]:
    keys: list[str] = []
    yield keys
    if os.environ.get("ACCEPTANCE_KEEP_ISSUES") == "1":
        print(f"\nIssues mantidas no sandbox: {', '.join(keys)}")
        return
    for key in keys:
        _delete(key)


def _get_json(user: User, path: str) -> Any:
    response = user.http.get(path, headers=user.headers)
    assert response.status_code == 200, response.text
    return response.json()


def _history(user: User, cid: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = _get_json(user, f"{BASE}/{cid}/messages")["items"]
    return items


def _titles(user: User) -> list[str]:
    return [c["title"] for c in _get_json(user, BASE)["items"]]


@pytest.mark.req("F07-RF-03")
def test_at_f07_01_retomar_conversa(owner: User) -> None:
    questions = [
        "Quero especificar o login com e-mail e senha da loja. Ainda não é para propor.",
        "Senha errada mostra 'E-mail ou senha incorretos'. Ainda não proponha.",
        "Resuma em uma frase o que combinamos até agora, sem propor nada.",
    ]
    first = owner.send(questions[0])
    turns = [first, *(owner.send(q, first.conversation_id) for q in questions[1:])]

    history = _history(owner, first.conversation_id)

    assert [m["role"] for m in history] == ["user", "assistant"] * 3
    assert [m["text"] for m in history if m["role"] == "user"] == questions
    assert [m["text"] for m in history if m["role"] == "assistant"] == [t.text for t in turns]
    assert not any("[Ação proposta" in m["text"] for m in history)


@pytest.mark.req("F07-RF-02")
@pytest.mark.req("F07-RF-04")
def test_at_f07_02_lista_ordenada_e_titulo_automatico(owner: User) -> None:
    login = owner.send("Vamos especificar o login com e-mail. Ainda não proponha nada.")
    checkout = owner.send(
        "Quero especificar o checkout da loja com pagamento por Pix. Ainda não proponha nada."
    )

    [top, second, *_] = _get_json(owner, BASE)["items"]
    assert (top["id"], second["id"]) == (checkout.conversation_id, login.conversation_id)
    assert re.search(r"checkout", top["title"], re.IGNORECASE), top

    renamed = owner.http.patch(
        f"{BASE}/{checkout.conversation_id}", json={"title": "Checkout v2"}, headers=owner.headers
    )
    assert renamed.status_code == 200, renamed.text
    owner.send("E o login, o que falta?", login.conversation_id)  # login sobe na lista
    owner.send("Pix com QR code e copia e cola. Não proponha.", checkout.conversation_id)

    titles = _titles(owner)
    assert titles[0] == "Checkout v2", titles


@pytest.mark.req("F07-RF-03")
def test_at_f07_03_cartoes_de_acao_persistem(owner: User, created: list[str]) -> None:
    turn = owner.send(ORDERS_STORY)
    [first] = _creates(turn)
    confirmed = owner.http.post(
        f"/api/v1/actions/{first['action_id']}/confirm", headers=owner.headers
    )
    assert confirmed.status_code == 200, confirmed.text
    created.append(confirmed.json()["result"]["issue_key"])
    second = owner.send(
        "Agora uma story para ordenar 'Meus pedidos' por data, mais recentes primeiro, com "
        "opção de mais antigos primeiro. Fora de escopo: outros campos. Testes: unidade e E2E. "
        "Pode propor.",
        turn.conversation_id,
    )
    [pending] = _creates(second)

    cards = {
        a["id"]: a
        for m in _history(owner, turn.conversation_id)
        if m["role"] == "assistant"
        for a in m["actions"]
    }

    done = cards[first["action_id"]]
    assert done["status"] == "done"
    assert done["result"]["url"].endswith(f"/browse/{done['result']['issue_key']}")
    assert cards[pending["action_id"]]["status"] == "pending"


@pytest.mark.req("F07-RF-05")
def test_at_f07_04_excluir_conversa(owner: User, created: list[str]) -> None:
    turn = owner.send(ORDERS_STORY)
    [proposed] = _creates(turn)
    done = owner.http.post(
        f"/api/v1/actions/{proposed['action_id']}/confirm", headers=owner.headers
    )
    assert done.status_code == 200, done.text
    key = done.json()["result"]["issue_key"]
    created.append(key)
    again = owner.send("Proponha a mesma story de novo, igual.", turn.conversation_id)
    pending = _creates(again)
    assert pending, again
    cid = turn.conversation_id

    response = owner.http.delete(f"{BASE}/{cid}", headers=owner.headers)

    assert response.status_code == 204, response.text
    assert cid not in [c["id"] for c in _get_json(owner, BASE)["items"]]
    assert owner.http.get(f"{BASE}/{cid}", headers=owner.headers).status_code == 404
    for action in pending:
        confirm = owner.http.post(
            f"/api/v1/actions/{action['action_id']}/confirm", headers=owner.headers
        )
        assert confirm.status_code == 404, confirm.text
    assert asyncio.run(_get(key)).key == key  # a issue continua no Jira


@pytest.mark.req("F07-RF-06")
def test_at_f07_05_projeto_padrao(owner: User) -> None:
    pinned = owner.http.post(BASE, json={"project_key": JIRA_PROJECT}, headers=owner.headers)
    assert pinned.status_code == 201, pinned.text
    cid = pinned.json()["id"]

    turn = owner.send(
        "Crie uma task de revisão de copy da tela de checkout: o botão principal passa de "
        "'Finalizar compra' para 'Concluir pedido'. Se o texto não couber no botão em telas de "
        "320 px, quebra em duas linhas sem cortar palavras. Fora de escopo: traduções. Testes: "
        "snapshot do componente e E2E do checkout. Pode propor.",
        cid,
    )

    [proposed] = _creates(turn)
    assert proposed["preview"]["project_key"] == JIRA_PROJECT, turn
    assert "qual projeto" not in turn.text.lower()
