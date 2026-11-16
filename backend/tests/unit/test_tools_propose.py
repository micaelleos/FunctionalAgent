"""Ferramentas de proposta: geram ação, nunca escrevem (F05-RF-04, F05-RF-05, RT-06, RT-13..15)."""

from typing import Any

import pytest

from app.agent.spec.jira_payload import (
    UPDATABLE_FIELDS,
    jira_create_fields,
    jira_update_fields,
    payload_hash,
)
from app.agent.tools.jira_tools import (
    NO_JIRA,
    propor_atualizacao_issue,
    propor_criacao_epico,
    propor_criacao_issue,
)
from tests.chat_fakes import FakeJiraReader, MemorySink, issue, tool_config
from tests.spec_fixtures import payments_epic, pix_story, pix_story_data

pytestmark = pytest.mark.req("F05-RF-04")


async def _create(spec: dict[str, Any], **extra: Any) -> tuple[str, MemorySink]:
    sink = MemorySink()
    args = {"project_key": "ABC", "spec": spec, **extra}
    out = await propor_criacao_issue.ainvoke(args, tool_config(FakeJiraReader(), sink))
    return out, sink


@pytest.mark.req("F05-RT-13")
async def test_proposta_de_historia_gera_acao_com_spec_canonica_e_previa() -> None:
    out, sink = await _create(pix_story_data())
    [action] = sink.actions

    assert action["kind"] == "create_issue"
    assert action["payload"] == {
        "project_key": "ABC",
        "issue_type": "Story",
        "spec": pix_story().model_dump(mode="json"),
        "labels": ["agent-ready", "specflow"],
    }
    assert action["preview"]["markdown"].startswith("## Objetivo\nComo cliente")
    assert action["preview"]["summary"] == "Permitir pagamento com Pix no checkout da loja"
    assert "aguardando confirmação" in out
    assert "Não diga que a issue foi criada" in out


@pytest.mark.req("F05-RT-14")
async def test_prontidao_vai_na_acao_e_avisa_sem_bloquear() -> None:
    sink = MemorySink()
    config = tool_config(FakeJiraReader(), sink)
    args = {"project_key": "ABC", "spec": pix_story_data(out_of_scope=[])}

    review = await propor_criacao_issue.ainvoke(args, config)
    assert review.startswith("Proposta não criada ainda: a spec não está pronta")
    assert "P-05 Fora de escopo" in review
    assert sink.actions == []

    out = await propor_criacao_issue.ainvoke(args, config)  # segunda vez: segue, sem bloquear
    readiness = sink.actions[0]["readiness"]

    assert readiness["ready"] is False
    assert {r["id"] for r in readiness["rules"] if not r["passed"]} == {"P-05"}
    assert sink.actions[0]["labels"] == ["specflow"]
    assert "NÃO pronta; falta: P-05 Fora de escopo" in out


@pytest.mark.req("F05-RT-15")
@pytest.mark.req("F05-RF-11")
async def test_human_only_leva_label_e_nao_agent_ready() -> None:
    _, sink = await _create(
        pix_story_data(human_only=True, human_only_reason="Troca o hash das senhas.")
    )
    assert sink.actions[0]["labels"] == ["human-only", "specflow"]


@pytest.mark.req("F05-RF-05")
async def test_projeto_inexistente_nao_gera_acao_e_pede_para_perguntar() -> None:
    sink = MemorySink()
    out = await propor_criacao_issue.ainvoke(
        {"project_key": "XYZ", "spec": pix_story_data()}, tool_config(FakeJiraReader(), sink)
    )

    assert sink.actions == []
    assert out.startswith("O projeto XYZ não existe")
    assert "Pergunte ao usuário" in out


@pytest.mark.req("F05-RT-06")
async def test_parent_so_entra_quando_informado() -> None:
    _, without = await _create(pix_story_data())
    _, with_parent = await _create(pix_story_data(), parent_key="ABC-7")

    assert "parent" not in jira_create_fields(without.actions[0]["payload"])
    assert jira_create_fields(with_parent.actions[0]["payload"])["parent"] == {"key": "ABC-7"}


@pytest.mark.req("F05-RT-05")
async def test_campos_do_jira_derivados_da_acao_com_descricao_em_adf() -> None:
    _, sink = await _create(pix_story_data())
    fields = jira_create_fields(sink.actions[0]["payload"])

    assert fields["project"] == {"key": "ABC"}
    assert fields["issuetype"] == {"name": "Story"}
    assert fields["description"]["type"] == "doc"
    assert fields["labels"] == ["agent-ready", "specflow"]


async def test_epico_proposto_com_decomposicao() -> None:
    sink = MemorySink()
    await propor_criacao_epico.ainvoke(
        {"project_key": "ABC", "spec": payments_epic().model_dump(mode="json")},
        tool_config(FakeJiraReader(), sink),
    )

    assert sink.actions[0]["payload"]["issue_type"] == "Epic"
    assert "## Decomposição" in sink.actions[0]["preview"]["markdown"]


async def test_hash_estavel_do_payload() -> None:
    _, a = await _create(pix_story_data())
    _, b = await _create(pix_story_data())
    assert payload_hash(a.actions[0]["payload"]) == payload_hash(b.actions[0]["payload"])


@pytest.mark.req("F05-RT-06")
async def test_atualizacao_so_muda_campos_permitidos_e_mantem_labels_alheias() -> None:
    current = issue("ABC-1", labels=("time-a", "agent-ready"))
    sink = MemorySink()
    await propor_atualizacao_issue.ainvoke(
        {"key": "ABC-1", "spec": pix_story_data(), "priority": "High"},
        tool_config(FakeJiraReader(issues=[current]), sink),
    )
    [action] = sink.actions
    fields = jira_update_fields(action["payload"])

    assert action["kind"] == "update_issue"
    assert set(fields) <= set(UPDATABLE_FIELDS)
    assert fields["labels"] == ["agent-ready", "specflow", "time-a"]
    assert fields["priority"] == {"name": "High"}


async def test_atualizacao_sem_nada_ou_de_issue_inexistente_nao_gera_acao() -> None:
    sink = MemorySink()
    config = tool_config(FakeJiraReader(issues=[issue("ABC-1")]), sink)

    assert (await propor_atualizacao_issue.ainvoke({"key": "ABC-1"}, config)).startswith("Nada")
    out = await propor_atualizacao_issue.ainvoke({"key": "ABC-9", "priority": "Low"}, config)
    assert "não existe" in out
    assert sink.actions == []


@pytest.mark.req("F05-RF-08")
async def test_sem_jira_nao_propoe() -> None:
    sink = MemorySink()
    out = await propor_criacao_issue.ainvoke(
        {"project_key": "ABC", "spec": pix_story_data()}, tool_config(None, sink)
    )
    assert out == NO_JIRA
    assert sink.actions == []


@pytest.mark.req("F05-RF-06")
async def test_cenario_sem_dado_volta_ao_modelo_sem_criar_acao() -> None:
    criterion = dict(pix_story_data()["acceptance_criteria"][1], given=[])
    out, sink = await _create(
        pix_story_data(acceptance_criteria=[pix_story_data()["acceptance_criteria"][0], criterion])
    )

    assert sink.actions == []
    assert out.startswith("Proposta não criada: os cenários CA-02")


@pytest.mark.req("F05-RF-11")
async def test_termo_sensivel_pede_confirmacao_uma_vez_e_depois_segue() -> None:
    sink = MemorySink()
    config = tool_config(FakeJiraReader(), sink)
    spec = pix_story_data(title="Trocar o algoritmo de hash das senhas para Argon2id")
    args = {"project_key": "ABC", "spec": spec}

    first = await propor_criacao_issue.ainvoke(args, config)
    second = await propor_criacao_issue.ainvoke(args, config)

    assert first.startswith("Proposta não criada ainda: a spec cita hash, argon2")
    assert "aguardando confirmação" in second
    assert len(sink.actions) == 1


@pytest.mark.req("F05-RF-11")
async def test_spec_ja_human_only_ou_sem_termos_nao_recebe_o_aviso() -> None:
    marked = pix_story_data(
        title="Trocar o algoritmo de hash das senhas para Argon2id",
        human_only=True,
        human_only_reason="Criptografia de senhas.",
    )
    out_marked, _ = await _create(marked)
    out_plain, _ = await _create(pix_story_data())  # "estorno" só em Fora de escopo

    assert "aguardando confirmação" in out_marked
    assert "aguardando confirmação" in out_plain
