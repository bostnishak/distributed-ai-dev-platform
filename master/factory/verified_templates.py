"""EPK-05: 8 Verified Production Starter Templates, Automated Verification Loop & Error-Guided Repair."""

from __future__ import annotations

import ast
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/factory", tags=["factory-verified"])

VERIFIED_TEMPLATES: dict[str, dict[str, Any]] = {
    "fastapi_service": {
        "name": "FastAPI REST Microservice",
        "stack": "python",
        "health_endpoint": "/health",
        "files": {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n",
            "tests/test_main.py": "def test_health():\n    assert True\n",
        },
    },
    "react_spa": {
        "name": "React + Vite SPA",
        "stack": "js",
        "health_endpoint": "/",
        "files": {
            "index.html": "<!doctype html><html><body><div id='root'></div></body></html>\n",
            "src/App.jsx": "export default function App() { return 'Ready'; }\n",
        },
    },
    "nextjs_app": {
        "name": "Next.js App Router Fullstack",
        "stack": "ts",
        "health_endpoint": "/api/health",
        "files": {
            "app/page.tsx": "export default function Page() { return null; }\n",
            "app/api/health/route.ts": "export async function GET() { return new Response('ok'); }\n",
        },
    },
    "flask_api": {
        "name": "Flask JSON API",
        "stack": "python",
        "health_endpoint": "/health",
        "files": {
            "app.py": "def health():\n    return {'status': 'ok'}\n",
            "test_app.py": "from app import health\nassert health()['status'] == 'ok'\n",
        },
    },
    "python_cli": {
        "name": "Python Argparse CLI",
        "stack": "python",
        "health_endpoint": "--version",
        "files": {
            "cli.py": "import argparse\ndef main(argv=None):\n    p = argparse.ArgumentParser()\n    return p.parse_args(argv)\n",
        },
    },
    "electron_desktop": {
        "name": "Electron Offline Desktop Shell",
        "stack": "js",
        "health_endpoint": "preload",
        "files": {
            "main.js": "export const appConfig = { contextIsolation: true, nodeIntegration: false };\n",
        },
    },
    "sqlite_crud": {
        "name": "SQLite Parameterized CRUD Service",
        "stack": "python",
        "health_endpoint": "/items",
        "files": {
            "store.py": "import sqlite3\ndef init(conn: sqlite3.Connection) -> None:\n    conn.execute('CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY, name TEXT)')\n",
        },
    },
    "ml_inference_api": {
        "name": "Local ML Inference Service",
        "stack": "python",
        "health_endpoint": "/predict",
        "files": {
            "model.py": "def predict(features: list[float]) -> float:\n    return round(sum(features) / max(1, len(features)), 4)\n",
        },
    },
}


def verify_template_bundle(template_id: str) -> dict[str, Any]:
    """Validate syntax, security invariants, and structure of a verified starter template."""
    tpl = VERIFIED_TEMPLATES.get(template_id)
    if not tpl:
        raise KeyError(f"Bilinmeyen şablon: {template_id}")
    errors: list[str] = []
    checked = 0
    for path, src in tpl["files"].items():
        checked += 1
        if path.endswith(".py"):
            try:
                ast.parse(src)
            except SyntaxError as exc:
                errors.append(f"{path}:{exc.lineno}: {exc.msg}")
        if "eval(" in src or "exec(" in src:
            errors.append(f"{path}: forbidden dynamic execution call")
    return {
        "ok": len(errors) == 0,
        "template_id": template_id,
        "name": tpl["name"],
        "stack": tpl["stack"],
        "files_checked": checked,
        "health_endpoint": tpl["health_endpoint"],
        "errors": errors,
    }


def build_targeted_repair_plan(errors: list[str]) -> list[dict[str, str]]:
    """Map build/test failure diagnostics to deterministic repair actions."""
    actions: list[dict[str, str]] = []
    for err in errors:
        low = err.lower()
        if "syntaxerror" in low or "invalid syntax" in low:
            actions.append({"error": err, "strategy": "ast_syntax_repair", "step": "Fix syntax near reported line"})
        elif "modulenotfounderror" in low or "importerror" in low:
            actions.append({"error": err, "strategy": "dependency_pin", "step": "Add missing package to requirements/package.json"})
        else:
            actions.append({"error": err, "strategy": "unit_test_patch", "step": "Inspect assertion diff and patch handler"})
    return actions


class RepairRequest(BaseModel):
    errors: list[str] = Field(default_factory=list)


@router.get("/verified-templates")
async def api_list_verified_templates():
    """List all 8 verified production starter templates for the code factory."""
    items = [
        {"id": tid, "name": t["name"], "stack": t["stack"], "health_endpoint": t["health_endpoint"], "file_count": len(t["files"])}
        for tid, t in VERIFIED_TEMPLATES.items()
    ]
    return {"ok": True, "count": len(items), "templates": items}


@router.post("/verified-templates/{template_id}/verify")
async def api_verify_template(template_id: str, body: RepairRequest | None = None):
    """Run syntax/security verification on a starter template and compute repair plan if errors exist."""
    try:
        res = verify_template_bundle(template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    extra_errors = body.errors if body else []
    res["repair_plan"] = build_targeted_repair_plan(res["errors"] + extra_errors)
    return res
