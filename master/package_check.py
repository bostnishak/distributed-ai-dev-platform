"""Slopsquatting guard: every dependency a generated project names must really exist on its registry.

Only package names are sent to PyPI / npm. A missing package or one published days ago is reported; when the registry
cannot be reached the check says so instead of passing silently.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_NEW_DAYS = 30
_MAX = 25

Lookup = Callable[[str, str], "dict | None"]


def declared(ws_dir: Path) -> list[tuple[str, str]]:
    """(registry, name) for requirements.txt and package.json dependencies."""
    found: list[tuple[str, str]] = []
    for req in ws_dir.rglob("requirements*.txt"):
        for line in req.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.lstrip().startswith(("#", "-")) and (match := _NAME_RE.match(line)):
                found.append(("pypi", match.group(1)))
    for manifest in ws_dir.rglob("package.json"):
        if "node_modules" in manifest.parts:
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        found += [("npm", n) for key in ("dependencies", "devDependencies") for n in data.get(key, {})]
    return list(dict.fromkeys(found))[:_MAX]


def registry_lookup(registry: str, name: str) -> dict | None:
    """Registry metadata, None when the package does not exist. OSError when the registry is unreachable."""
    url = f"https://pypi.org/pypi/{name}/json" if registry == "pypi" else f"https://registry.npmjs.org/{name.replace('/', '%2F')}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "dependency-check"}), timeout=8) as resp:
            return json.loads(resp.read(8_000_000))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _first_release(registry: str, data: dict) -> datetime | None:
    if registry == "pypi":
        stamps = [f.get("upload_time_iso_8601", "") for files in data.get("releases", {}).values() for f in files]
    else:
        stamps = [data.get("time", {}).get("created", "")]
    parsed = [datetime.fromisoformat(s.replace("Z", "+00:00")) for s in stamps if s]
    return min(parsed) if parsed else None


def check(ws_dir: Path, lookup: Lookup = registry_lookup, now: datetime | None = None) -> list[str]:
    now = now or datetime.now(UTC)
    problems: list[str] = []
    for registry, name in declared(ws_dir):
        try:
            data = lookup(registry, name)
        except (OSError, ValueError):
            return [*problems, "Paket kayıtlarına ulaşılamadı; bağımlılık adları doğrulanmadı."]
        if data is None:
            problems.append(f"'{name}' paketi {registry} kayıtlarında yok (uydurma ad olabilir; kurmayın)")
            continue
        born = _first_release(registry, data)
        if born and (now - born).days < _NEW_DAYS:
            problems.append(f"'{name}' paketi yalnızca {(now - born).days} günlük; kurmadan önce kaynağını doğrulayın")
    return problems


def report(ws_dir: Path) -> str:
    found = check(ws_dir)
    return "Bağımlılık denetimi: " + "; ".join(found[:4]) if found else ""
