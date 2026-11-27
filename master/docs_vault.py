"""Library facts pinned to a version, cached on disk, so the writer does not code against an invented or old API.

For each library a request names, the current version and summary come from the registry and are cached for 14 days.
Offline, the cached entry is used and says how old it is; with no entry nothing is claimed.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from pathlib import Path

import config
import package_check

_FRESH_S = 14 * 86_400
KNOWN = {
    "fastapi": "pypi", "pydantic": "pypi", "sqlalchemy": "pypi", "flask": "pypi", "django": "pypi", "httpx": "pypi", "pandas": "pypi",
    "typer": "pypi", "streamlit": "pypi", "pytest": "pypi", "react": "npm", "vue": "npm", "express": "npm", "tailwindcss": "npm", "vite": "npm",
}


def named(request: str) -> list[tuple[str, str]]:
    lowered = request.casefold()
    return [(registry, name) for name, registry in KNOWN.items() if re.search(rf"\b{name}\b", lowered)][:5]


def _vault() -> Path:
    return config.data_dir() / "docs_vault"


def _entry(registry: str, data: dict) -> dict:
    if registry == "pypi":
        info = data.get("info", {})
        return {"version": info.get("version", ""), "summary": info.get("summary", ""), "requires_python": info.get("requires_python") or ""}
    latest = data.get("dist-tags", {}).get("latest", "")
    return {"version": latest, "summary": data.get("description", ""), "requires_python": ""}


def lookup(registry: str, name: str, fetch: Callable[[str, str], dict | None] = package_check.registry_lookup, now: float | None = None) -> dict | None:
    """{version, summary, requires_python, fetched, stale} or None when it was never seen and cannot be fetched."""
    now = now or time.time()
    path = _vault() / f"{registry}-{name}.json"
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cached = None
    if cached and now - cached["fetched"] < _FRESH_S:
        return {**cached, "stale": False}
    try:
        data = fetch(registry, name)
    except (OSError, ValueError):
        return {**cached, "stale": True} if cached else None
    if not data:
        return None
    entry = {**_entry(registry, data), "fetched": now}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
    return {**entry, "stale": False}


def brief(request: str, fetch: Callable[[str, str], dict | None] = package_check.registry_lookup) -> str:
    lines = []
    for registry, name in named(request):
        if entry := lookup(registry, name, fetch):
            age = f" (önbellekten, {time.strftime('%Y-%m-%d', time.localtime(entry['fetched']))} tarihli)" if entry["stale"] else ""
            lines.append(f"- {name} {entry['version']}{age}: {entry['summary'][:100]}")
    if not lines:
        return ""
    return "\n\nKÜTÜPHANE SÜRÜMLERİ (kayıttan doğrulandı; bu sürümlerin API'sini kullan, kaldırılmış eski kullanımlardan kaçın):\n" + "\n".join(lines)
