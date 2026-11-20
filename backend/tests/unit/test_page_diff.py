"""Diff por seção da proposta de atualização (F20-RF-03, F20-RT-04)."""

import pytest

from app.services.page_diff import MAX_SIDE, section_diff, sections

BEFORE = """# Glossário

Intro.

## Termos
| Termo | Definição |
|---|---|
| Pedido | compra |

## Antigos
x
"""
AFTER = """# Glossário

Intro.

## Termos
| Termo | Definição |
|---|---|
| Pedido | compra   confirmada |

## Novos
Cliente
"""


@pytest.mark.req("F20-RF-03")
@pytest.mark.req("F20-RT-04")
def test_secoes_alteradas_novas_e_removidas() -> None:
    diff = section_diff(BEFORE, AFTER)
    assert [(d["section"], d["change"]) for d in diff] == [
        ("Termos", "changed"),
        ("Novos", "added"),
        ("Antigos", "removed"),
    ]
    assert "compra   confirmada" in diff[0]["after"]
    assert "| compra |" in diff[0]["before"]


@pytest.mark.req("F20-RT-04")
def test_espacos_nao_contam_e_pagina_nova_e_toda_adicionada() -> None:
    assert section_diff(BEFORE, BEFORE.replace("Intro.", "Intro.  ")) == []
    created = section_diff("", AFTER)
    assert [d["change"] for d in created] == ["added", "added", "added"]
    assert sections("")[:1] == []


@pytest.mark.req("F20-RT-04")
def test_lado_grande_e_cortado() -> None:
    diff = section_diff("", "## A\n" + "x" * (MAX_SIDE + 10))
    assert len(diff[0]["after"]) == MAX_SIDE + 2
