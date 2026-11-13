"""Testes do script de rastreabilidade (F01-RT-07)."""

from pathlib import Path

import pytest
import trace_requirements as tr

SPEC = """# F99 — Teste

| Campo | Valor |
|---|---|
| **Status** | {status} |

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F99-RF-01 | Coberto por teste | Must |
| F99-RF-02 | Validado manualmente | Must |
| F99-RF-03 | Sem teste | Must |

### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F99-RF-01 | x | ⬜ |
| F99-RF-02 | roteiro manual | ✅ |
| F99-RF-03 | — | ⬜ |

### 11. Evidências
"""


def _setup(tmp_path: Path, status: str) -> tuple[Path, Path]:
    specs = tmp_path / "docs" / "modernizacao" / "features"
    specs.mkdir(parents=True)
    (specs / "F99-teste.md").write_text(SPEC.format(status=status), encoding="utf-8")
    tests = tmp_path / "backend" / "tests"
    tests.mkdir(parents=True)
    (tests / "test_x.py").write_text(
        '@pytest.mark.req("F99-RF-01")\n', encoding="utf-8"
    )
    return specs, tmp_path


@pytest.mark.parametrize("status", ["Em validação", "Aceita", "Em produção"])
def test_falha_quando_spec_obrigatoria_tem_requisito_sem_teste(
    tmp_path: Path, status: str
) -> None:
    specs, root = _setup(tmp_path, status)

    _, missing = tr.check(specs, root)

    assert missing == ["F99-RF-03"]
    assert tr.main(["--specs", str(specs), "--root", str(root)]) == 1


def test_rascunho_e_apenas_informativo(tmp_path: Path) -> None:
    specs, root = _setup(tmp_path, "Rascunho")

    report, missing = tr.check(specs, root)

    assert missing == []
    assert "1/3" not in report[0]
    assert "2/3 (informativo)" in report[0]


def test_specs_reais_do_repositorio_sao_lidas() -> None:
    spec = tr.parse_spec(tr.SPECS_DIR / "F01-monorepo-e-ci.md")

    assert spec.requirements[0].endswith("-RF-01")
    assert len(spec.requirements) == 5
