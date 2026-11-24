"""EPK-04: Generate JSDoc API contract typedefs from FastAPI OpenAPI schema into master/static/js/api_types.js."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MASTER_DIR = REPO_ROOT / "master"
if str(MASTER_DIR) not in sys.path:
    sys.path.insert(0, str(MASTER_DIR))


def _json_type_to_js(prop: dict[str, Any]) -> str:
    t = prop.get("type")
    if t == "string":
        return "string"
    if t in ("integer", "number"):
        return "number"
    if t == "boolean":
        return "boolean"
    if t == "array":
        return "Array<*>"
    if t == "object":
        return "Object"
    return "*"


def generate_api_types_js(out_path: Path | None = None) -> Path:
    """Export canonical OpenAPI response schemas and path count into a compact JSDoc JS module."""
    import app as master_app

    schema = master_app.app.openapi()
    schemas = schema.get("components", {}).get("schemas", {})
    paths = sorted(schema.get("paths", {}).keys())

    lines = [
        "// Auto-generated from FastAPI OpenAPI schema by scripts/gen_api_types.py (EPK-04).",
        "// Run: ./master/venv/Scripts/python.exe scripts/gen_api_types.py",
        "",
        f"export const API_CONTRACT_VERSION = {json.dumps(schema.get('info', {}).get('version', '1.0.0'))};",
        f"export const API_ROUTE_COUNT = {len(paths)};",
        "",
    ]
    for name in sorted(schemas.keys()):
        if not name.endswith("Response") and name != "ApiEnvelope":
            continue
        props = schemas[name].get("properties") or {}
        lines.append(f"/** @typedef {{{name}}} {name}_Contract")
        for pname, pdef in sorted(props.items()):
            lines.append(f" * @property {{{_json_type_to_js(pdef)}}} [{pname}]")
        lines.append(" */")
    lines.append("export const API_SCHEMA_NAMES = " + json.dumps(sorted(schemas.keys())) + ";")
    lines.append("")

    target = out_path or (MASTER_DIR / "static" / "js" / "api_types.js")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


if __name__ == "__main__":
    out = generate_api_types_js()
    sys.stdout.write(f"Generated {out}\n")
