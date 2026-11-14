#!/usr/bin/env python3
"""Exporta o contrato OpenAPI do backend para frontend/openapi.json (Constituição V).

O CI regenera e falha se o arquivo commitado estiver desatualizado; o front gera os tipos do
cliente a partir dele (`npm run gen:api`).
"""

import json
import sys
from pathlib import Path

from app.main import create_app

OUT = Path(__file__).resolve().parents[1] / "frontend" / "openapi.json"


def main() -> int:
    schema = create_app().openapi()
    schema["info"]["version"] = "v1"  # sem o SHA do build: o arquivo só muda quando o contrato muda
    OUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"OpenAPI exportado em {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
