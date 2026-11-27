"""Known vulnerabilities in the pinned dependencies of a project, from the free OSV database (api.osv.dev).

Only package names and versions are sent. "bağımlılık denetimi" checks the chat's project (or the platform itself);
the night summary runs the same check.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

import httpx

_ASK_RE = re.compile(r"^\s*bağımlılık\s+(?:açığı\s+)?denetimi\s*[.!?]?\s*$", re.IGNORECASE)
_PIN_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*==\s*([A-Za-z0-9.+!-]+)")
_URL = "https://api.osv.dev/v1"
_LIMIT = 200

Post = Callable[[str, dict], dict]


def pinned(project: Path) -> list[tuple[str, str, str]]:
    """(ecosystem, name, version) of every exactly pinned dependency."""
    found: list[tuple[str, str, str]] = []
    for requirements in sorted(project.glob("requirements*.txt")):
        for line in requirements.read_text(encoding="utf-8", errors="replace").splitlines():
            if match := _PIN_RE.match(line):
                found.append(("PyPI", match[1], match[2]))
    lock = project / "package-lock.json"
    if lock.is_file():
        try:
            packages = json.loads(lock.read_text(encoding="utf-8")).get("packages", {})
        except ValueError:
            packages = {}
        found += [("npm", key.rsplit("node_modules/", 1)[-1], str(value["version"])) for key, value in packages.items() if key and value.get("version")]
    return list(dict.fromkeys(found))[:_LIMIT]


def _post(path: str, body: dict) -> dict:
    return httpx.post(f"{_URL}{path}", json=body, timeout=30).raise_for_status().json()


def audit(project: Path, post: Post = _post) -> tuple[int, list[str]]:
    """(dependencies checked, one line per vulnerable one). httpx.HTTPError when the database cannot be reached."""
    dependencies = pinned(project)
    if not dependencies:
        return 0, []
    queries = [{"package": {"ecosystem": eco, "name": name}, "version": version} for eco, name, version in dependencies]
    results = post("/querybatch", {"queries": queries}).get("results", [])
    lines = []
    for (_eco, name, version), result in zip(dependencies, results, strict=False):
        ids = [v["id"] for v in result.get("vulns", [])]
        if ids:
            lines.append(f"- {name} {version}: {len(ids)} bilinen açık ({', '.join(ids[:4])})")
    return len(dependencies), lines


def report(project: Path, label: str, post: Post = _post) -> str:
    try:
        checked, lines = audit(project, post)
    except (httpx.HTTPError, ValueError, KeyError, OSError) as exc:
        return f"Bağımlılık denetimi yapılamadı (OSV'ye ulaşılamadı): {type(exc).__name__}"
    if not checked:
        return f"{label}: sürümü sabitlenmiş bağımlılık bulunamadı (`paket==sürüm`), denetlenecek bir şey yok."
    if not lines:
        return f"{label}: {checked} bağımlılık denetlendi, OSV'de bilinen açık yok."
    return "\n".join([f"{label}: {checked} bağımlılığın {len(lines)} tanesinde bilinen açık var:", *lines, "", "Ayrıntı: https://osv.dev/<kimlik>"])


def answer(prompt: str, ws_dir: Path | None, platform_dir: Path, post: Post = _post) -> str:
    """The reply to "bağımlılık denetimi"; "" for other messages."""
    if not _ASK_RE.match(prompt):
        return ""
    if ws_dir is not None and ws_dir.is_dir():
        return report(ws_dir, "Bu proje", post)
    return report(platform_dir, "Platformun kendisi", post)
