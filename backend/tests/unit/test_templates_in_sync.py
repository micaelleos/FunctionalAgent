"""Os modelos do backend são cópia fiel de docs/metodologia/modelos/ (F20-RT-05)."""

from pathlib import Path

import pytest

from app.agent.docs_model import SPACE_TREE, TEMPLATE_FILES, fill, labels_for, template

DOCS = Path(__file__).resolve().parents[3] / "docs" / "metodologia" / "modelos"


@pytest.mark.req("F20-RT-05")
@pytest.mark.parametrize(("kind", "name"), sorted(TEMPLATE_FILES.items()))
def test_modelo_igual_ao_da_metodologia(kind: str, name: str) -> None:
    assert template(kind) == (DOCS / name).read_text("utf-8")


@pytest.mark.req("F20-RT-05")
def test_arvore_do_espaco_tem_9_paginas_com_pai_antes_do_filho() -> None:
    refs: list[str] = []
    for page in SPACE_TREE:
        assert page.parent is None or page.parent in refs
        assert template(page.template)
        refs.append(page.ref)
    assert len(SPACE_TREE) == 9
    assert labels_for("glossario") == ["specflow", "specflow-tipo-glossario"]
    assert fill(template("constituicao"), "Loja", "LOJA").startswith("# Constituição — Loja")
