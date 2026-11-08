"""API contract checker: compare frontend fetch() calls against backend routes (PB-40).

Scans all JS files for fetch('/api/...') calls and compares against
the FastAPI application's registered routes. Reports mismatches.
"""

from __future__ import annotations

import re
from pathlib import Path

import config


_FETCH_RE = re.compile(r"""fetch\s*\(\s*[`'"](\/api\/[^`'"?\s]+)""")
_TEMPLATE_RE = re.compile(r"""\$\{[^}]+\}""")


def _extract_frontend_routes(js_dir: Path) -> set[str]:
    """Scan JS files and return a set of /api/ path prefixes used in fetch() calls."""
    routes: set[str] = set()
    for js_file in js_dir.glob("**/*.js"):
        try:
            text = js_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in _FETCH_RE.finditer(text):
            path = match.group(1)
            # Normalise template literals: /api/agents/${id}/tasks → /api/agents/{id}/tasks
            path = _TEMPLATE_RE.sub("{id}", path)
            # Strip trailing slash
            routes.add(path.rstrip("/"))
    return routes


def _extract_backend_routes(app) -> set[str]:
    """Return all /api/ route paths registered with the FastAPI app."""
    routes: set[str] = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/"):
            routes.add(path.rstrip("/"))
    return routes


def run_check(app) -> dict:
    """Run the contract check and return a report dict."""
    js_dir = config.STATIC_DIR / "js"
    frontend = _extract_frontend_routes(js_dir)
    backend = _extract_backend_routes(app)

    missing_in_backend = sorted(frontend - backend)
    not_called_by_frontend = sorted(backend - frontend)

    return {
        "frontend_routes": sorted(frontend),
        "backend_routes": sorted(backend),
        "missing_in_backend": missing_in_backend,
        "not_called_by_frontend": not_called_by_frontend,
        "ok": len(missing_in_backend) == 0,
    }
