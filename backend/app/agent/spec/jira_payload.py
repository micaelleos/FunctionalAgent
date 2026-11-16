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
    spec: WorkItemSpec | EpicSpec, project_key: str, labels: list[str], parent_key: str | None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "project_key": project_key,
        "issue_type": ISSUE_TYPES[spec.type],
        "spec": spec.model_dump(mode="json"),
        "labels": sorted(labels),
    }
    if parent_key:  # D07: `parent` só quando informado
        payload["parent_key"] = parent_key
    return payload


def update_payload(
    issue_key: str,
    spec: WorkItemSpec | EpicSpec | None,
    priority: str | None,
    labels: list[str] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"issue_key": issue_key}
    if spec is not None:
        payload["spec"] = spec.model_dump(mode="json")
    if priority:
        payload["priority"] = priority
    if labels is not None:
        payload["labels"] = sorted(labels)
    return payload


def spec_of(payload: dict[str, Any]) -> WorkItemSpec | EpicSpec | None:
    raw = payload.get("spec")
    return None if raw is None else _SPEC.validate_python(raw)


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
    return fields


def jira_update_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Corpo de `PUT /rest/api/3/issue/{key}` (`fields`), restrito a `UPDATABLE_FIELDS`."""
    fields: dict[str, Any] = {}
    spec = spec_of(payload)
    if spec is not None:
        fields["summary"] = spec.title
        fields["description"] = to_adf(spec)
    if payload.get("priority"):
        fields["priority"] = {"name": payload["priority"]}
    if "labels" in payload:
        fields["labels"] = list(payload["labels"])
    assert set(fields) <= set(UPDATABLE_FIELDS)  # noqa: S101
    return fields
