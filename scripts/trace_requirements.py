#!/usr/bin/env python3
"""Rastreabilidade requisito → teste (Constituição, Artigo I.2 / F01-RT-07).

Lê as specs em docs/modernizacao/features/*.md e procura os IDs dos requisitos
funcionais (Fxx-RF-nn) nos arquivos de teste do repositório.

Um requisito está coberto quando:
  * seu ID aparece em algum arquivo de teste (ex.: @pytest.mark.req("F05-RF-01")
    ou describe("F05-RF-01 ...")), ou
  * a linha dele na matriz de rastreabilidade da spec está marcada com ✅
    (validação manual ou de pipeline, com evidência registrada na spec).

Falha (exit 1) se uma spec com status "Em validação", "Aceita" ou "Em produção"
tiver requisito sem cobertura. Specs em outros status aparecem só no relatório.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = ROOT / "docs" / "modernizacao" / "features"
TEST_GLOBS = (
    "backend/tests/**/*.py",
    "frontend/src/**/*.test.ts",
    "frontend/src/**/*.test.tsx",
    "frontend/e2e/**/*.ts",
    "scripts/**/test_*.py",
)
ENFORCED_STATUSES = ("em validação", "aceita", "em produção")

RF_ROW = re.compile(r"^\|\s*(F\d{2}-RF-\d{2})\s*\|", re.MULTILINE)
STATUS = re.compile(r"^\|\s*\*\*Status\*\*\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)
TRACE_SECTION = re.compile(
    r"###\s*10\.\s*Rastreabilidade(.*?)(?:\n###\s|\Z)", re.DOTALL
)
CHECKED_ROW = re.compile(r"^\|\s*(F\d{2}-RF-\d{2})\s*\|.*✅", re.MULTILINE)


@dataclass
class Spec:
    path: Path
    status: str
    requirements: list[str]
    checked: set[str] = field(default_factory=set)

    @property
    def enforced(self) -> bool:
        return self.status.lower().startswith(ENFORCED_STATUSES)


def parse_spec(path: Path) -> Spec:
    text = path.read_text(encoding="utf-8")
    status_match = STATUS.search(text)
    status = (
        status_match.group(1).split("(")[0].strip() if status_match else "Desconhecido"
    )
    trace = TRACE_SECTION.search(text)
    trace_text = trace.group(1) if trace else ""
    requirements = list(dict.fromkeys(RF_ROW.findall(text)))
    return Spec(path, status, requirements, set(CHECKED_ROW.findall(trace_text)))


def collect_test_text(root: Path) -> str:
    chunks: list[str] = []
    for pattern in TEST_GLOBS:
        for file in root.glob(pattern):
            if "node_modules" in file.parts:
                continue
            chunks.append(file.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def check(specs_dir: Path, root: Path) -> tuple[list[str], list[str]]:
    """Retorna (linhas do relatório, requisitos obrigatórios sem cobertura)."""
    tests = collect_test_text(root)
    report: list[str] = []
    missing: list[str] = []
    for path in sorted(specs_dir.glob("F*.md")):
        spec = parse_spec(path)
        uncovered = [
            r for r in spec.requirements if r not in tests and r not in spec.checked
        ]
        covered = len(spec.requirements) - len(uncovered)
        flag = "OBRIGATÓRIO" if spec.enforced else "informativo"
        report.append(
            f"{path.stem:<40} {spec.status:<18} {covered}/{len(spec.requirements)} ({flag})"
        )
        if spec.enforced:
            missing.extend(uncovered)
    return report, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--specs", type=Path, default=SPECS_DIR)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)

    report, missing = check(args.specs, args.root)
    print("Rastreabilidade de requisitos funcionais (cobertos/total):")
    print("\n".join(f"  {line}" for line in report))
    if missing:
        print("\nRequisitos sem teste em specs obrigatórias:")
        print("\n".join(f"  - {req}" for req in missing))
        return 1
    print("\nOK: todos os requisitos de specs em validação/produção têm teste.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
