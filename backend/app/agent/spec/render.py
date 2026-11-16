"""Renderiza um `AgentReadySpec` em Markdown e ADF (Jira API v3), seções fixas (RA-02, F05-RT-13).

As seções são montadas uma única vez (`sections`) e os dois formatos saem dessa estrutura, para que
o texto no Jira e o Markdown copiado para um agente de código nunca divirjam. Títulos e ordem são
fixos; seções obrigatórias aparecem mesmo vazias, as opcionais só quando têm conteúdo.
"""

from dataclasses import dataclass
from typing import Any

from app.agent.spec.adf import inline_to_adf
from app.agent.spec.schema import EpicSpec, Scenario, WorkItemSpec

EMPTY = "(não preenchido)"
NO_QUESTIONS = "(nenhuma)"

# Ordem e títulos fixos (doc 10 §4.2).
WORK_ITEM_SECTIONS: tuple[str, ...] = (
    "Objetivo",
    "Contexto",
    "Critérios de aceite",
    "Fora de escopo",
    "Restrições e contratos",
    "Onde mexer",
    "Como verificar",
    "Dependências",
    "Perguntas em aberto",
)
EPIC_SECTIONS: tuple[str, ...] = (
    "Objetivo",
    "Problema",
    "Benefícios",
    "Escopo",
    "Fora de escopo",
    "Critérios de aceite do épico",
    "Decomposição",
    "Restrições",
    "Riscos",
    "Perguntas em aberto",
)
HUMAN_ONLY_NOTE = "Não indicada para agente de código"


@dataclass(frozen=True)
class Paragraph:
    text: str


@dataclass(frozen=True)
class Bullets:
    items: tuple[str, ...]


@dataclass(frozen=True)
class Criterion:
    heading: str
    lines: tuple[str, ...]


Block = Paragraph | Bullets | Criterion


@dataclass(frozen=True)
class Section:
    title: str
    blocks: tuple[Block, ...]


def _gherkin(scenario: Scenario) -> tuple[str, ...]:
    lines: list[str] = []
    for keyword, steps in (
        ("Dado", scenario.given),
        ("Quando", scenario.when),
        ("Então", scenario.then),
    ):
        lines.extend(f"{keyword if i == 0 else 'E'} {step}" for i, step in enumerate(steps))
    return tuple(lines)


def _criterion(scenario: Scenario) -> Criterion:
    return Criterion(f"{scenario.id} ({scenario.kind.value}) {scenario.title}", _gherkin(scenario))


def _text(value: str, *, required: bool) -> tuple[Block, ...] | None:
    if value:
        return (Paragraph(value),)
    return (Paragraph(EMPTY),) if required else None


def _bullets(items: list[str], *, required: bool, empty: str = EMPTY) -> tuple[Block, ...] | None:
    if items:
        return (Bullets(tuple(items)),)
    return (Paragraph(empty),) if required else None


def _work_item_blocks(spec: WorkItemSpec) -> dict[str, tuple[Block, ...] | None]:
    criteria: tuple[Block, ...] = tuple(_criterion(s) for s in spec.acceptance_criteria) or (
        Paragraph(EMPTY),
    )
    return {
        "Objetivo": _text(spec.objective, required=True),
        "Contexto": _bullets(spec.context, required=True),
        "Critérios de aceite": criteria,
        "Fora de escopo": _bullets(spec.out_of_scope, required=True),
        "Restrições e contratos": _bullets(spec.constraints, required=False),
        "Onde mexer": _bullets(spec.where_to_change, required=False),
        "Como verificar": _bullets(spec.how_to_verify, required=True),
        "Dependências": _bullets(list(spec.dependencies), required=False),
        "Perguntas em aberto": _bullets(spec.open_questions, required=True, empty=NO_QUESTIONS),
    }


def _epic_blocks(spec: EpicSpec) -> dict[str, tuple[Block, ...] | None]:
    decomposition = [
        f"{item.key + ' · ' if item.key else ''}{item.title}"
        + (f" (depende de {', '.join(item.depends_on)})" if item.depends_on else "")
        for item in spec.decomposition
    ]
    return {
        "Objetivo": _text(spec.objective, required=True),
        "Problema": _text(spec.problem, required=True),
        "Benefícios": _bullets(spec.benefits, required=True),
        "Escopo": _bullets(spec.scope, required=True),
        "Fora de escopo": _bullets(spec.out_of_scope, required=True),
        "Critérios de aceite do épico": _bullets(spec.acceptance_criteria, required=True),
        "Decomposição": _bullets(decomposition, required=True),
        "Restrições": _bullets(spec.constraints, required=False),
        "Riscos": _bullets(spec.risks, required=False),
        "Perguntas em aberto": _bullets(spec.open_questions, required=True, empty=NO_QUESTIONS),
    }


def sections(spec: WorkItemSpec | EpicSpec) -> tuple[Section, ...]:
    """Seções da spec, na ordem fixa, sem as opcionais vazias."""
    if isinstance(spec, EpicSpec):
        order, blocks = EPIC_SECTIONS, _epic_blocks(spec)
    else:
        order, blocks = WORK_ITEM_SECTIONS, _work_item_blocks(spec)
    result = [Section(title, content) for title in order if (content := blocks[title]) is not None]
    if spec.human_only:
        note = Section(HUMAN_ONLY_NOTE, (Paragraph(spec.human_only_reason),))
        result.insert(0, note)
    return tuple(result)


# ---------------------------------------------------------------- Markdown


def _markdown_block(block: Block) -> str:
    if isinstance(block, Paragraph):
        return block.text
    if isinstance(block, Bullets):
        return "\n".join(f"- {item}" for item in block.items)
    return "\n".join([f"**{block.heading}**", *block.lines])


def to_markdown(spec: WorkItemSpec | EpicSpec) -> str:
    """Markdown da descrição (sem o título, que vai no campo Summary do Jira)."""
    parts = []
    for section in sections(spec):
        body = "\n\n".join(_markdown_block(b) for b in section.blocks)
        parts.append(f"## {section.title}\n{body}")
    return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------- ADF (Atlassian Document Format)


def _adf_inline(text: str, *, strong: bool = False) -> list[dict[str, Any]]:
    """Texto da spec em ADF; o Markdown inline (código, negrito, links) vira marcas (RT-05)."""
    nodes = inline_to_adf(text) or [{"type": "text", "text": text}]
    if strong:
        for node in nodes:
            if node.get("type") == "text":
                node["marks"] = [*node.get("marks", []), {"type": "strong"}]
    return nodes


def _adf_paragraph(content: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "paragraph", "content": content}


def _adf_lines(lines: tuple[str, ...]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        if i:
            content.append({"type": "hardBreak"})
        content.extend(_adf_inline(line))
    return content


def _adf_block(block: Block) -> list[dict[str, Any]]:
    if isinstance(block, Paragraph):
        return [_adf_paragraph(_adf_inline(block.text))]
    if isinstance(block, Bullets):
        items = [
            {"type": "listItem", "content": [_adf_paragraph(_adf_inline(i))]} for i in block.items
        ]
        return [{"type": "bulletList", "content": items}]
    nodes = [_adf_paragraph(_adf_inline(block.heading, strong=True))]
    if block.lines:
        nodes.append(_adf_paragraph(_adf_lines(block.lines)))
    return nodes


def to_adf(spec: WorkItemSpec | EpicSpec) -> dict[str, Any]:
    """Descrição em ADF para `POST /rest/api/3/issue` (mesmas seções e ordem do Markdown)."""
    content: list[dict[str, Any]] = []
    for section in sections(spec):
        content.append(
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": section.title}],
            }
        )
        for block in section.blocks:
            content.extend(_adf_block(block))
    return {"type": "doc", "version": 1, "content": content}
