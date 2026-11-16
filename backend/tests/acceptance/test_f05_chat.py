"""AT-F05-01..09: conversa com o agente, com Gemini real e o Jira sandbox (spec F05 §5).

O modelo não é determinístico: as verificações olham a estrutura (eventos, ações, labels,
seções), não o texto exato.
"""

import os
import re

import pytest

from app.integrations.jira.client import JiraClient
from tests.acceptance.conftest import JIRA, JIRA_PROJECT, User, new_user


async def _recent_keys() -> list[str]:
    async with JiraClient(JIRA["site_url"], JIRA["email"], JIRA["api_token"]) as jira:
        issues = await jira.search(f"project = {JIRA_PROJECT} ORDER BY created DESC", 50)
    return [i.key for i in issues]


@pytest.mark.req("F05-RF-01")
@pytest.mark.req("F05-RT-12")
def test_at_f05_01_resposta_em_streaming(po: User) -> None:
    turn = po.send("Olá, o que você faz?")

    assert turn.kinds().count("token") >= 2
    assert turn.kinds()[-2:] == ["message_saved", "done"]
    assert turn.first_token_s is not None
    assert turn.first_token_s < float(os.environ.get("ACCEPTANCE_FIRST_TOKEN_S", "3"))


@pytest.mark.req("F05-RF-02")
@pytest.mark.req("F05-RT-01")
def test_at_f05_02_memoria_por_conversa_e_isolamento(no_jira: User) -> None:
    first = no_jira.send("Meu produto se chama Zeta. Responda só 'anotado'.")
    again = no_jira.send("Qual o nome do meu produto?", first.conversation_id)
    other = new_user(with_jira=False).send("Qual o nome do meu produto?")

    assert "zeta" in again.text.lower()
    assert "zeta" not in other.text.lower()


@pytest.mark.req("F05-RF-03")
@pytest.mark.req("F05-RF-07")
def test_at_f05_03_consulta_ao_jira(po: User) -> None:
    turn = po.send("Quais projetos eu tenho no Jira?")
    names = [e["data"]["name"] for e in turn.events if e["event"] == "tool_start"]

    assert "listar_projetos" in names
    assert "tool_end" in turn.kinds()
    assert JIRA_PROJECT in turn.text


@pytest.mark.req("F05-RF-04")
@pytest.mark.req("F05-RF-06")
@pytest.mark.req("F05-RT-13")
@pytest.mark.req("F05-RT-14")
async def test_at_f05_04_criacao_vira_spec_pronta_proposta_e_sem_escrita(po: User) -> None:
    before = await _recent_keys()
    turn = po.send(
        f"Crie no projeto {JIRA_PROJECT} uma story para login com e-mail e senha; senha errada "
        "mostra 'E-mail ou senha incorretos'. Após 5 tentativas erradas a conta bloqueia por 15 "
        "minutos. Fora de escopo: login social. Testes: unidade e E2E do login. Pode propor."
    )
    [action] = [a for a in turn.actions() if a["kind"] == "create_issue"]
    preview = action["preview"]
    md = preview["markdown"]

    assert preview["issue_type"] == "Story"
    for section in (
        "Objetivo",
        "Contexto",
        "Critérios de aceite",
        "Fora de escopo",
        "Como verificar",
    ):
        assert f"## {section}\n" in md
    assert re.search(r"\*\*CA-\d{2} \(erro\)", md)
    assert "E-mail ou senha incorretos" in md
    assert preview["readiness"]["ready"] is True, preview["readiness"]
    assert "agent-ready" in preview["labels"]
    assert await _recent_keys() == before


@pytest.mark.req("F05-RF-05")
def test_at_f05_05_projeto_nao_informado(po: User) -> None:
    turn = po.send("Crie uma story de logout")

    assert turn.actions() == []
    assert "projeto" in turn.text.lower()


@pytest.mark.req("F05-RF-08")
def test_at_f05_06_sem_conexao_jira(no_jira: User) -> None:
    first = no_jira.send("Escreva um épico de onboarding de novos clientes")
    second = no_jira.send("Envie ao Jira", first.conversation_id)

    text = first.text.lower()
    for word in ("objetivo", "benefícios", "escopo", "critérios"):
        assert word in text
    assert second.actions() == []
    assert re.search(r"configura|settings|conect", second.text.lower())


@pytest.mark.req("F05-RF-09")
def test_at_f05_07_falta_informacao_pergunta_antes_de_propor(po: User) -> None:
    turn = po.send(f"Crie no {JIRA_PROJECT} uma story de exportar relatório")

    assert turn.actions() == []
    assert "?" in turn.text


@pytest.mark.req("F05-RF-10")
def test_at_f05_08_pedido_grande_vira_epico_decomposto(po: User) -> None:
    turn = po.send(
        f"Crie no {JIRA_PROJECT} o módulo de assinaturas: planos, cobrança recorrente, "
        "cancelamento, troca de plano e notas fiscais. Siga com o que tiver e deixe as dúvidas em "
        "perguntas em aberto."
    )
    epics = [a for a in turn.actions() if a["preview"]["issue_type"] == "Epic"]

    assert epics, turn.text
    assert "## Decomposição\n" in epics[0]["preview"]["markdown"]
    for action in turn.actions():
        if action["preview"]["issue_type"] != "Epic":
            assert action["preview"]["markdown"].count("**CA-") <= 8


@pytest.mark.req("F05-RF-11")
def test_at_f05_09_mudanca_sensivel_marcada_para_humano(po: User) -> None:
    turn = po.send(
        f"Crie no {JIRA_PROJECT} uma story para trocar o algoritmo de hash das senhas para "
        "Argon2id, migrando no próximo login. Fora de escopo: troca forçada. Testes de unidade. "
        "Pode propor."
    )
    [action] = turn.actions()

    assert "human-only" in action["preview"]["labels"]
    assert "agent-ready" not in action["preview"]["labels"]
