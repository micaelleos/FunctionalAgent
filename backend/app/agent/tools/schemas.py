"""Esquemas das ferramentas no formato que o Gemini aceita.

O conversor do `langchain-google-genai` ignora `$defs`/`$ref` e transforma o objeto em STRING;
por isso o modelo recebe cada ferramenta como dicionário com as referências resolvidas. A
execução continua nas ferramentas reais, que validam os argumentos com Pydantic.
"""

import copy
from typing import Any

from langchain_core.tools import BaseTool

_DROP = {"discriminator", "title", "$defs"}


def inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    defs: dict[str, Any] = schema.get("$defs", {})

    def walk(node: Any, *, in_properties: bool = False) -> Any:
        if isinstance(node, list):
            return [walk(item) for item in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            target = copy.deepcopy(defs[node["$ref"].rsplit("/", 1)[-1]])
            extra = {k: v for k, v in node.items() if k != "$ref"}
            return walk({**target, **extra})
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key == "properties":
                out[key] = {name: walk(prop) for name, prop in value.items()}
            elif key == "oneOf":
                out["anyOf"] = walk(value)
            elif key in _DROP and not in_properties:
                continue
            else:
                out[key] = walk(value)
        return out

    result: dict[str, Any] = walk(schema)
    return result


def model_tool_specs(tools: list[BaseTool]) -> list[dict[str, Any]]:
    """Definições no formato de função (`{"type": "function", ...}`) para `bind_tools`."""
    specs = []
    for tool in tools:
        schema = tool.tool_call_schema
        if isinstance(schema, dict):
            params = dict(schema)
        elif hasattr(schema, "model_json_schema"):
            params = schema.model_json_schema()
        else:  # pragma: no cover - pydantic v1 não é usado
            params = schema.schema()
        specs.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": inline_refs(params),
                },
            }
        )
    return specs
