"""Esquema `AgentReadySpec` (ADR-007, doc 10 §4.2): a spec estruturada de onde sai cada issue.

O esquema valida a forma (tipos, IDs, tamanhos), mas aceita specs incompletas: o que falta para um
agente de código implementar é papel da verificação de prontidão (`readiness.py`), que avisa e não
bloqueia (RA-22).
"""

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# Textos curtos (um item de lista, uma linha de cenário) e longos (objetivo, problema).
Line = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
IssueKey = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]+-\d+$")]
ScenarioId = Annotated[str, StringConstraints(pattern=r"^CA-\d{2}$")]

MAX_ITEMS = 30


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ScenarioKind(StrEnum):
    PRINCIPAL = "principal"
    ALTERNATIVO = "alternativo"
    ERRO = "erro"
    BORDA = "borda"


class Scenario(_Strict):
    """Critério de aceite em Gherkin (RA-04).

    A primeira linha de cada parte leva Dado/Quando/Então; as seguintes, "E".
    """

    id: ScenarioId
    kind: ScenarioKind
    title: Line
    # Obrigatórios no esquema (o modelo sempre os envia); listas vazias só vêm de issues lidas do
    # Jira, e a prontidão (P-03) aponta o que falta.
    given: list[Line] = Field(max_length=10, description="Pré-condições (Dado); pelo menos 1")
    when: list[Line] = Field(max_length=10, description="Ação (Quando); pelo menos 1")
    then: list[Line] = Field(max_length=10, description="Resultado esperado (Então); pelo menos 1")


class SpecType(StrEnum):
    STORY = "story"
    TASK = "task"
    EPIC = "epic"


class Reference(_Strict):
    """Página usada como fonte (F19-RF-06): complementa o texto da spec, nunca o substitui."""

    title: Title
    url: Annotated[str, StringConstraints(pattern=r"^https://[^\s]+$", max_length=1000)]


MAX_REFERENCES = 10


class _Common(_Strict):
    title: Title
    objective: Text = ""
    out_of_scope: list[Line] = Field(default_factory=list, max_length=MAX_ITEMS)
    open_questions: list[Line] = Field(default_factory=list, max_length=MAX_ITEMS)
    # RA-24: mudança não indicada para agente de código (segurança, dados pessoais, autenticação…).
    human_only: bool = False
    human_only_reason: Text = ""
    # Fontes da documentação do projeto (Confluence, F19); seção "Referências" no fim do issue.
    references: list[Reference] = Field(default_factory=list, max_length=MAX_REFERENCES)

    @model_validator(mode="after")
    def _human_only_has_reason(self) -> "_Common":
        if self.human_only and not self.human_only_reason:
            raise ValueError("human_only exige human_only_reason")
        return self


class WorkItemSpec(_Common):
    """História ou tarefa: cabe em um PR (RA-10)."""

    type: Literal[SpecType.STORY, SpecType.TASK]
    context: list[Line] = Field(default_factory=list, max_length=MAX_ITEMS)
    acceptance_criteria: list[Scenario] = Field(default_factory=list, max_length=MAX_ITEMS)
    constraints: list[Line] = Field(default_factory=list, max_length=MAX_ITEMS)
    where_to_change: list[Line] = Field(default_factory=list, max_length=MAX_ITEMS)
    how_to_verify: list[Line] = Field(default_factory=list, max_length=MAX_ITEMS)
    dependencies: list[IssueKey] = Field(default_factory=list, max_length=MAX_ITEMS)

    @model_validator(mode="after")
    def _unique_scenario_ids(self) -> "WorkItemSpec":
        ids = [s.id for s in self.acceptance_criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("IDs de critérios de aceite repetidos")
        return self


class DecompositionItem(_Strict):
    """História prevista no épico (RA-11): chave quando já existe e dependências entre elas."""

    title: Title
    key: IssueKey | None = None
    depends_on: list[IssueKey] = Field(default_factory=list, max_length=MAX_ITEMS)


class EpicSpec(_Common):
    type: Literal[SpecType.EPIC]
    problem: Text = ""
    benefits: list[Line] = Field(default_factory=list, max_length=MAX_ITEMS)
    scope: list[Line] = Field(default_factory=list, max_length=MAX_ITEMS)
    acceptance_criteria: list[Line] = Field(default_factory=list, max_length=MAX_ITEMS)
    decomposition: list[DecompositionItem] = Field(default_factory=list, max_length=MAX_ITEMS)
    constraints: list[Line] = Field(default_factory=list, max_length=MAX_ITEMS)
    risks: list[Line] = Field(default_factory=list, max_length=MAX_ITEMS)


AgentReadySpec = Annotated[WorkItemSpec | EpicSpec, Field(discriminator="type")]


def canonical_json(spec: WorkItemSpec | EpicSpec) -> str:
    """Forma canônica da spec; o hash conferido na confirmação sai dela (ADR-003, ADR-007)."""
    return json.dumps(
        spec.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def spec_hash(spec: WorkItemSpec | EpicSpec) -> str:
    return hashlib.sha256(canonical_json(spec).encode()).hexdigest()
