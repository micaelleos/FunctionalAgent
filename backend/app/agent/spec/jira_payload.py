"""Payload das ações propostas e os campos do Jira que saem dele (F05-RT-06, ADR-003, ADR-007).

O payload guardado em `pending_actions` é a forma canônica: o hash conferido na confirmação (F06)
é calculado sobre ele e os campos do Jira são derivados de forma determinística, sem LLM.
"""

import hashlib
import json
from typing import Any

from pydantic import TypeAdapter

from app.agent.spec.render import to_adf
from app.agent.spec.schema import AgentReadySpec, EpicSpec, SpecType, WorkItemSpec

ISSUE_TYPES = {SpecType.STORY: "Story", SpecType.TASK: "Task", SpecType.EPIC: "Epic"}
# Campos que uma atualização pode mudar (corrige D06): nada além destes chega ao Jira.
UPDATABLE_FIELDS = ("summary", "description", "priority", "labels")

_SPEC: TypeAdapter[WorkItemSpec | EpicSpec] = TypeAdapter(AgentReadySpec)


def canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(payload).encode()).hexdigest()


def create_payload(
    spec: WorkItemSpec | EpicSpec,
    project_key: str,
    labels: list[str],
    parent_key: str | None,
    priority: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "project_key": project_key,
        "issue_type": ISSUE_TYPES[spec.type],
        "spec": spec.model_dump(mode="json"),
        "labels": sorted(labels),
    }
    if parent_key:  # D07: `parent` só quando informado
        payload["parent_key"] = parent_key
    if priority:  # sem prioridade, vale o padrão do projeto
        payload["priority"] = priority
    return payload


def update_payload(
    issue_key: str,
    spec: WorkItemSpec | EpicSpec | None,
    priority: str | None,
    labels: list[str] | None,
    summary: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"issue_key": issue_key}
    if spec is not None:
        payload["spec"] = spec.model_dump(mode="json")
    elif summary:  # só o título; a descrição atual fica
        payload["summary"] = summary
    if priority:
        payload["priority"] = priority
    if labels is not None:
        payload["labels"] = sorted(labels)
    return payload


def spec_of(payload: dict[str, Any]) -> WorkItemSpec | EpicSpec | None:
    raw = payload.get("spec")
    return None if raw is None else _SPEC.validate_python(raw)


# Nomes do tipo nos idiomas do Jira Cloud (o site define os nomes; projetos podem renomear).
_TYPE_NAMES = {
    "Story": {"story", "user story", "história", "historia", "história de usuário", "estória"},
    "Task": {"task", "tarefa", "tarea", "tâche", "aufgabe"},
}


def resolve_issue_type(issue_type: str, available: list[tuple[str, str, int]]) -> str | None:
    """Id do tipo no projeto para o tipo lógico do payload (`Story`, `Task`, `Epic`).

    `available`: (id, nome, nível de hierarquia) de cada tipo do projeto. Épico é o tipo de nível
    1; história e tarefa são de nível 0 e se distinguem pelo nome. Sem correspondência: `None`."""
    if issue_type == "Epic":
        epics = [i for i, _, level in available if level == 1]
        return epics[0] if len(epics) == 1 else None
    names = _TYPE_NAMES.get(issue_type, {issue_type.lower()})
    for type_id, name, level in available:
        if level == 0 and name.strip().lower() in names:
            return type_id
    return None


def jira_create_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Corpo de `POST /rest/api/3/issue` (`fields`) para uma ação `create_issue` confirmada."""
    spec = spec_of(payload)
    assert spec is not None  # noqa: S101 - create sempre tem spec
    fields: dict[str, Any] = {
        "project": {"key": payload["project_key"]},
        "issuetype": {"name": payload["issue_type"]},
        "summary": spec.title,
        "description": to_adf(spec),
        "labels": list(payload["labels"]),
    }
    if payload.get("parent_key"):
        fields["parent"] = {"key": payload["parent_key"]}
    if payload.get("priority"):
        fields["priority"] = {"name": payload["priority"]}
    return fields


def jira_update_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Corpo de `PUT /rest/api/3/issue/{key}` (`fields`), restrito a `UPDATABLE_FIELDS`."""
    fields: dict[str, Any] = {}
    spec = spec_of(payload)
    if spec is not None:
        fields["summary"] = spec.title
        fields["description"] = to_adf(spec)
    elif payload.get("summary"):
        fields["summary"] = payload["summary"]
    if payload.get("priority"):
        fields["priority"] = {"name": payload["priority"]}
    if "labels" in payload:
        fields["labels"] = list(payload["labels"])
    assert set(fields) <= set(UPDATABLE_FIELDS)  # noqa: S101
    return fields
