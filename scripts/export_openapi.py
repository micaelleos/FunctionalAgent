#!/usr/bin/env python3
"""Exporta o contrato OpenAPI do backend para frontend/openapi.json (Constituição V) e o esquema
dos eventos SSE do chat para docs/api/sse-events.v1.json (F05-RT-12).

O CI regenera e falha se o arquivo commitado estiver desatualizado; o front gera os tipos do
cliente a partir dele (`npm run gen:api`).
"""

import json
import sys
from pathlib import Path

from app.main import create_app
from app.services.chat_events import SCHEMA_VERSION, json_schema

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "openapi.json"
SSE_OUT = ROOT / "docs" / "api" / f"sse-events.v{SCHEMA_VERSION}.json"


def main() -> int:
    schema = create_app().openapi()
    schema["info"]["version"] = "v1"  # sem o SHA do build: o arquivo só muda quando o contrato muda
    OUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"OpenAPI exportado em {OUT}")
    SSE_OUT.parent.mkdir(parents=True, exist_ok=True)
    SSE_OUT.write_text(json.dumps(json_schema(), indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"Esquema SSE exportado em {SSE_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
