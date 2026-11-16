"""Prontidão para agente de código e labels (F05-RT-14, F05-RT-15, F05-RF-11; doc 10 §4.4)."""

from typing import Any

import pytest

from app.agent.spec.readiness import Severity, evaluate, labels_for, load_config
from tests.spec_fixtures import payments_epic, pix_story, pix_story_data

pytestmark = pytest.mark.req("F05-RT-14")


def _failed(spec: Any) -> set[str]:
    return {r.id for r in evaluate(spec).results if not r.passed}


def test_historia_do_exemplo_esta_pronta_sem_avisos() -> None:
    readiness = evaluate(pix_story())

    assert readiness.ready
    assert (readiness.missing, readiness.warnings) == ((), ())
    assert [r.id for r in readiness.results] == [f"P-{n:02d}" for n in range(1, 11)]
    assert readiness.config_version == "v1"


@pytest.mark.parametrize(
    ("title", "detail"),
    [
        ("Pagamento com Pix no checkout da loja", "não começa com verbo no infinitivo"),
        ("Permitir Pix", "2 palavras"),
        ("Permitir " + "muito " * 20 + "Pix", "22 palavras"),
    ],
)
def test_p01_titulo(title: str, detail: str) -> None:
    result = evaluate(pix_story(title=title)).results[0]

    assert (result.id, result.passed) == ("P-01", False)
    assert detail in result.detail


def test_p02_objetivo_vazio() -> None:
    assert _failed(pix_story(objective="")) == {"P-02"}


def test_p03_sem_criterios_ou_criterio_incompleto_ou_criterios_demais() -> None:
    data = pix_story_data()
    incomplete = dict(data["acceptance_criteria"][0], then=[])
    many = [dict(data["acceptance_criteria"][0], id=f"CA-{i:02d}") for i in range(1, 10)]

    assert "P-03" in _failed(pix_story(acceptance_criteria=[]))
    assert _failed(pix_story(acceptance_criteria=[incomplete, data["acceptance_criteria"][1]])) == {
        "P-03"
    }
    result = evaluate(pix_story(acceptance_criteria=many)).results[2]
    assert "9 critérios (esperado de 1 a 8)" in result.detail


def test_p04_sem_cenario_de_erro_ou_borda() -> None:
    only_happy = [pix_story_data()["acceptance_criteria"][0]]
    readiness = evaluate(pix_story(acceptance_criteria=only_happy))

    assert {r.id for r in readiness.missing} == {"P-04"}
    assert readiness.missing[0].label == "Cenário de erro ou de borda"


def test_p05_p06_p07() -> None:
    assert _failed(pix_story(out_of_scope=[])) == {"P-05"}
    assert _failed(pix_story(how_to_verify=[])) == {"P-06"}
    result = evaluate(pix_story(open_questions=["Qual o prazo do QR Code?"])).results[6]
    assert (result.id, result.passed, result.detail) == (
        "P-07",
        False,
        "1 pergunta(s) sem resposta",
    )


def test_p08_termos_vagos_avisam_sem_derrubar_a_prontidao() -> None:
    spec = pix_story(objective="Deixar o checkout rápido e intuitivo, melhorar a conversão etc.")
    readiness = evaluate(spec)
    p08 = readiness.warnings[0]

    assert readiness.ready
    assert (p08.id, p08.severity) == ("P-08", Severity.WARNING)
    assert p08.detail == "termos: rápido, intuitivo, etc, melhorar"


def test_p08_melhorar_com_numero_na_frase_nao_e_vago() -> None:
    assert "P-08" not in _failed(pix_story(objective="Melhorar a conversão de 62% para 70%."))


def test_p09_corpo_longo() -> None:
    long_context = ["palavra " * 40] * 16
    assert _failed(pix_story(context=long_context)) == {"P-09"}


def test_p10_depende_de_link() -> None:
    linked = ["Ver documento em https://wiki.example.com/pix para as regras."]
    assert _failed(pix_story(context=linked)) == {"P-10"}
    # Link como complemento de um corpo completo não é problema.
    complement = ["Histórico em https://wiki.example.com/pix (complemento)."]
    assert "P-10" not in _failed(pix_story(context=complement))


def test_epico_usa_p03_de_decomposicao_e_dispensa_p04_e_p06() -> None:
    readiness = evaluate(payments_epic())

    assert readiness.ready
    assert [r.id for r in readiness.results] == [
        "P-01",
        "P-02",
        "P-03",
        "P-05",
        "P-07",
        "P-08",
        "P-09",
        "P-10",
    ]
    assert (
        "sem decomposição em histórias"
        in evaluate(payments_epic(decomposition=[])).missing[0].detail
    )


def test_parametros_versionados_vem_do_arquivo_do_prompt() -> None:
    cfg = load_config()

    assert (cfg.title_min_words, cfg.title_max_words, cfg.max_criteria) == (5, 20, 8)
    assert any(t.term == "melhorar" and t.unless_number for t in cfg.vague_terms)


@pytest.mark.req("F05-RT-15")
def test_labels_specflow_sempre_agent_ready_so_quando_pronta() -> None:
    ready = pix_story()
    not_ready = pix_story(out_of_scope=[])

    assert labels_for(ready, evaluate(ready)) == ("specflow", "agent-ready")
    assert labels_for(not_ready, evaluate(not_ready)) == ("specflow",)


@pytest.mark.req("F05-RT-15")
@pytest.mark.req("F05-RF-11")
def test_human_only_nunca_leva_agent_ready() -> None:
    spec = pix_story(human_only=True, human_only_reason="Troca o algoritmo de hash das senhas.")
    readiness = evaluate(spec)

    assert readiness.ready
    assert labels_for(spec, readiness) == ("specflow", "human-only")
