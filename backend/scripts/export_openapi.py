"""Write the OpenAPI schema to frontend/src/api/openapi.json (input for type generation)."""

import json
from pathlib import Path

from football_ai.main import create_app

out = Path(__file__).resolve().parents[2] / "frontend" / "src" / "api" / "openapi.json"
out.write_text(json.dumps(create_app().openapi(), indent=1, ensure_ascii=False) + "\n")
print(f"scritto {out}")
