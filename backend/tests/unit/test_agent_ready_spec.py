"""`AgentReadySpec` e renderização com seções fixas (F05-RF-06, F05-RT-13; ADR-007, doc 10 §4.2)."""

from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from app.agent.spec.render import EPIC_SECTIONS, WORK_ITEM_SECTIONS, to_adf, to_markdown
from app.agent.spec.schema import AgentReadySpec, EpicSpec, WorkItemSpec, spec_hash
from tests.spec_fixtures import PIX_MARKDOWN, payments_epic, pix_story, pix_story_data

pytestmark = [pytest.mark.req("F05-RF-06"), pytest.mark.req("F05-RT-13")]

ADAPTER: TypeAdapter[WorkItemSpec | EpicSpec] = TypeAdapter(AgentReadySpec)


def _headings(adf: dict[str, Any]) -> list[str]:
    return [n["content"][0]["text"] for n in adf["content"] if n["type"] == "heading"]


def test_markdown_da_historia_igual_ao_exemplo_do_doc_10() -> None:
    assert to_markdown(pix_story()) == PIX_MARKDOWN


def test_adf_tem_as_mesmas_secoes_na_mesma_ordem_do_markdown() -> None:
    spec = pix_story()
    adf = to_adf(spec)
    md_headings = [line[3:] for line in to_markdown(spec).splitlines() if line.startswith("## ")]

    assert (adf["type"], adf["version"]) == ("doc", 1)
    assert _headings(adf) == md_headings
    assert all(h in WORK_ITEM_SECTIONS for h in md_headings)


def test_adf_do_criterio_tem_titulo_em_negrito_e_linhas_gherkin() -> None:
    adf = to_adf(pix_story())
    texts = [n for n in adf["content"] if n["type"] == "paragraph"]
    heading = next(p for p in texts if p["content"][0]["text"].startswith("CA-02"))
    body = texts[texts.index(heading) + 1]["content"]

    assert heading["content"][0]["marks"] == [{"type": "strong"}]
    assert [n["text"] for n in body if n["type"] == "text"] == [
        "Dado o provedor responde 503",
        'Quando escolho "Pix"',
        'Então vejo "Pix indisponível no momento. Tente cartão ou aguarde alguns minutos."',
        'E o pedido continua com status "aguardando pagamento"',
    ]
    assert sum(n["type"] == "hardBreak" for n in body) == 3


def test_secoes_obrigatorias_aparecem_mesmo_vazias_e_opcionais_somem() -> None:
    spec = WorkItemSpec.model_validate({"type": "task", "title": "Configurar o provedor OIDC"})
    md = to_markdown(spec)

    assert [h[3:] for h in md.splitlines() if h.startswith("## ")] == [
        "Objetivo",
        "Contexto",
        "Critérios de aceite",
        "Fora de escopo",
        "Como verificar",
        "Perguntas em aberto",
    ]
    assert "(não preenchido)" in md
    assert md.endswith("## Perguntas em aberto\n(nenhuma)\n")


def test_epico_tem_secoes_proprias_e_decomposicao_com_dependencias() -> None:
    epic = payments_epic()
    md = to_markdown(epic)

    assert [h[3:] for h in md.splitlines() if h.startswith("## ")] == [
        s for s in EPIC_SECTIONS if s not in ("Restrições", "Riscos")
    ]
    assert "- PAG-121 · Permitir pagamento com Pix no checkout" in md
    assert "- Permitir pagamento com boleto (depende de PAG-121)" in md
    assert _headings(to_adf(epic))[-1] == "Perguntas em aberto"


def test_human_only_abre_a_descricao_com_o_motivo() -> None:
    spec = pix_story(human_only=True, human_only_reason="Mexe no hash das senhas.")

    assert to_markdown(spec).startswith("## Não indicada para agente de código\nMexe no hash")


def test_tipo_discrimina_historia_e_epico() -> None:
    assert isinstance(ADAPTER.validate_python(pix_story_data()), WorkItemSpec)
    assert isinstance(ADAPTER.validate_python(payments_epic().model_dump()), EpicSpec)


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"extra": "x"}, "Extra inputs"),
        ({"title": ""}, "at least 1 character"),
        ({"dependencies": ["pag-1"]}, "pattern"),
        ({"human_only": True}, "human_only exige human_only_reason"),
        (
            {"acceptance_criteria": [pix_story_data()["acceptance_criteria"][0]] * 2},
            "IDs de critérios de aceite repetidos",
        ),
    ],
)
def test_esquema_recusa_forma_invalida(overrides: dict[str, Any], error: str) -> None:
    with pytest.raises(ValidationError, match=error):
        WorkItemSpec.model_validate(pix_story_data(**overrides))


def test_id_de_criterio_segue_ca_nn() -> None:
    criterion = dict(pix_story_data()["acceptance_criteria"][0], id="CA-1")
    with pytest.raises(ValidationError, match="pattern"):
        WorkItemSpec.model_validate(pix_story_data(acceptance_criteria=[criterion]))


def test_hash_canonico_estavel_e_sensivel_ao_conteudo() -> None:
    a = pix_story()
    b = WorkItemSpec.model_validate_json(a.model_dump_json())

    assert spec_hash(a) == spec_hash(b)
    assert spec_hash(a) != spec_hash(
        pix_story(title="Permitir pagamento com Pix no checkout do app")
    )


def test_spaces_nas_bordas_sao_removidos() -> None:
    assert pix_story(title="  Permitir pagamento com Pix no checkout  ").title.endswith("checkout")
