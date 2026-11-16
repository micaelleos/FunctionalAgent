"""Lê uma issue existente (Markdown vindo do ADF do Jira) de volta para um `AgentReadySpec`.

Usado por `avaliar_prontidao` (F05-RF-12, RA-25). Issues criadas pelo SpecFlow voltam completas,
porque as seções têm títulos fixos; issues escritas à mão viram uma spec parcial e a verificação
de prontidão aponta o que falta. Nunca falha: texto fora das seções conhecidas vai para "Contexto".
"""

import re
from typing import Any

from app.agent.spec.render import EMPTY as EMPTY_TEXT
from app.agent.spec.render import EPIC_SECTIONS, HUMAN_ONLY_NOTE, NO_QUESTIONS, WORK_ITEM_SECTIONS
from app.agent.spec.schema import MAX_ITEMS, EpicSpec, WorkItemSpec

_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")
_CRITERION = re.compile(r"^\*\*(CA-\d{2})\s+\((principal|alternativo|erro|borda)\)\s*(.*?)\*\*$")
_DECOMP = re.compile(r"^(?:([A-Z][A-Z0-9_]+-\d+) · )?(.+?)(?: \(depende de ([^)]+)\))?$")
_KEY = re.compile(r"^[A-Z][A-Z0-9_]+-\d+$")
_STEP = {"dado": "given", "quando": "when", "então": "then", "entao": "then"}
_PLACEHOLDERS = {EMPTY_TEXT, NO_QUESTIONS, "(nenhum)", "-"}
_LINE_MAX = 500


def _clip(text: str) -> str:
    return text if len(text) <= _LINE_MAX else text[: _LINE_MAX - 1] + "…"


def _split_sections(markdown: str) -> tuple[list[str], dict[str, list[str]]]:
    """Linhas antes do primeiro título conhecido e as linhas de cada seção conhecida."""
    known = {s.lower(): s for s in (*WORK_ITEM_SECTIONS, *EPIC_SECTIONS, HUMAN_ONLY_NOTE)}
    preamble: list[str] = []
    sections: dict[str, list[str]] = {}
    current: list[str] = preamble
    for line in markdown.splitlines():
        match = _HEADING.match(line.strip())
        title = known.get(match.group(1).strip().rstrip(":").lower()) if match else None
        if title:
            current = sections.setdefault(title, [])
        else:
            current.append(line.rstrip())
    return preamble, sections


def _items(lines: list[str]) -> list[str]:
    items: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or line in _PLACEHOLDERS:
            continue
        if line.startswith(("- ", "* ")):
            items.append(_clip(line[2:].strip()))
        elif re.match(r"^\d+\.\s", line):
            items.append(_clip(line.split(" ", 1)[1].strip()))
        elif items and raw.startswith("  "):
            items[-1] = _clip(f"{items[-1]} {line}")
        else:
            items.append(_clip(line))
    return items[:MAX_ITEMS]


def _text(lines: list[str]) -> str:
    text = " ".join(line.strip() for line in lines if line.strip() not in _PLACEHOLDERS)
    return text.strip()[:2000]


def _criteria(lines: list[str]) -> list[dict[str, Any]]:
    criteria: list[dict[str, Any]] = []
    last = "given"
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        header = _CRITERION.match(line)
        if header:
            cid, kind, title = header.groups()
            criteria.append(
                {
                    "id": cid,
                    "kind": kind,
                    "title": title or cid,
                    "given": [],
                    "when": [],
                    "then": [],
                }
            )
            last = "given"
            continue
        if not criteria:
            continue
        word, _, rest = line.partition(" ")
        key = word.lower()
        if key in _STEP and rest:
            last = _STEP[key]
            criteria[-1][last].append(_clip(rest))
        elif key == "e" and rest:
            criteria[-1][last].append(_clip(rest))
    unique: dict[str, dict[str, Any]] = {}
    for criterion in criteria:
        unique.setdefault(criterion["id"], criterion)
    return list(unique.values())[:MAX_ITEMS]


def _decomposition(lines: list[str]) -> list[dict[str, Any]]:
    out = []
    for item in _items(lines):
        match = _DECOMP.match(item)
        if not match:
            continue  # pragma: no cover - o padrão aceita qualquer texto
        key, title, deps = match.groups()
        depends = [d.strip() for d in (deps or "").split(",") if _KEY.match(d.strip())]
        out.append({"title": title[:255], "key": key, "depends_on": depends})
    return out


def _title(summary: str) -> str:
    return summary.strip()[:255] or "(sem título)"


def parse_issue(summary: str, issue_type: str, markdown: str) -> WorkItemSpec | EpicSpec:
    preamble, sec = _split_sections(markdown)
    loose = _items(preamble)
    human_reason = _text(sec.get(HUMAN_ONLY_NOTE, []))
    common: dict[str, Any] = {
        "title": _title(summary),
        "objective": _text(sec.get("Objetivo", [])),
        "out_of_scope": _items(sec.get("Fora de escopo", [])),
        "open_questions": _items(sec.get("Perguntas em aberto", [])),
        "human_only": bool(human_reason),
        "human_only_reason": human_reason,
    }
    if issue_type.lower() in {"epic", "épico", "epico"}:
        return EpicSpec.model_validate(
            {
                **common,
                "type": "epic",
                "problem": _text(sec.get("Problema", [])),
                "benefits": _items(sec.get("Benefícios", [])),
                "scope": (_items(sec.get("Escopo", [])) + loose)[:MAX_ITEMS],
                "acceptance_criteria": _items(sec.get("Critérios de aceite do épico", [])),
                "decomposition": _decomposition(sec.get("Decomposição", [])),
                "constraints": _items(sec.get("Restrições", [])),
                "risks": _items(sec.get("Riscos", [])),
            }
        )
    deps = [d for d in _items(sec.get("Dependências", [])) if _KEY.match(d)]
    kind = "task" if issue_type.lower() in {"task", "tarefa", "subtask", "subtarefa"} else "story"
    return WorkItemSpec.model_validate(
        {
            **common,
            "type": kind,
            "context": (_items(sec.get("Contexto", [])) + loose)[:MAX_ITEMS],
            "acceptance_criteria": _criteria(sec.get("Critérios de aceite", [])),
            "constraints": _items(sec.get("Restrições e contratos", [])),
            "where_to_change": _items(sec.get("Onde mexer", [])),
            "how_to_verify": _items(sec.get("Como verificar", [])),
            "dependencies": deps,
        }
    )
