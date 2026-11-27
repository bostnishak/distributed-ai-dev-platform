"""API contract checker: compare frontend fetch() calls against backend routes (PB-40).

Scans all JS files for fetch('/api/...') calls and compares against
the FastAPI application's registered routes. Reports mismatches.
"""

from __future__ import annotations

import re
from pathlib import Path

import config

_API_REF_RE = re.compile(r"""[`'"](\/api\/[^`'"?\s]+)""")
_TEMPLATE_RE = re.compile(r"""\$\{[^}]+\}""")
_PARAM_RE = re.compile(r"""\{[^}]+\}""")


def _normalize_path(path: str) -> str:
    """Normalize dynamic segments (${x} or {user_id}) to a canonical {param} token."""
    # Strip trailing query interpolation appended directly to a filename/segment (e.g. backup.zip${q})
    cleaned = re.sub(r"""(?<!/)\$\{[^}]+\}$""", "", path)
    norm = _TEMPLATE_RE.sub("{param}", cleaned)
    norm = _PARAM_RE.sub("{param}", norm)
    return norm.rstrip("/")


def _extract_frontend_routes(js_dir: Path) -> set[str]:
    """Scan JS files and return a set of normalized /api/ paths used by the UI."""
    routes: set[str] = set()
    for js_file in js_dir.glob("**/*.js"):
        try:
            text = js_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in _API_REF_RE.finditer(text):
            raw = match.group(1)
            # Strip trailing file/preview suffixes inside dynamic download URLs if needed
            routes.add(_normalize_path(raw))
    return routes


def _all_routes(routes):
    """Every route, including those of included routers (kept as nested objects by newer FastAPI versions)."""
    for route in routes:
        inner = getattr(route, "original_router", None)
        if inner is None:
            yield route
        else:
            yield from _all_routes(inner.routes)


def _extract_backend_routes(app) -> set[str]:
    """Return all normalized /api/ route paths registered with the FastAPI app (including included routers)."""
    routes: set[str] = set()
    openapi = getattr(app, "openapi", None)
    if callable(openapi):
        schema = openapi()
        paths = schema.get("paths") if isinstance(schema, dict) else None
        for path in (paths or {}):
            if path.startswith("/api/"):
                routes.add(_normalize_path(path))
    for route in _all_routes(app.routes):  # WebSocket routes are not in the OpenAPI schema
        path = getattr(route, "path", "")
        if path.startswith("/api/"):
            routes.add(_normalize_path(path))
    return routes


def run_check(app) -> dict:
    """Run the contract check and return a report dict."""
    js_dir = config.STATIC_DIR / "js"
    frontend = _extract_frontend_routes(js_dir)
    backend = _extract_backend_routes(app)

    # Allow prefix matches for wildcard/path-param routes such as /api/studio/workspaces/{param}/preview/{param}
    missing_in_backend = sorted(
        f for f in frontend
        if f not in backend
        and not any(b.endswith("/{param}") and f.startswith(b[: -len("{param}")]) for b in backend)
    )
    not_called_by_frontend = sorted(
        b for b in backend
        if b not in frontend
        and not any(b.endswith("/{param}") and f.startswith(b[: -len("{param}")]) for f in frontend)
    )

    return {
        "frontend_routes": sorted(frontend),
        "backend_routes": sorted(backend),
        "missing_in_backend": missing_in_backend,
        "not_called_by_frontend": not_called_by_frontend,
        "ok": len(missing_in_backend) == 0,
    }
