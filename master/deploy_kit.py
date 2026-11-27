"""Hardened Docker files for a generated Python web project, written by code, plus a lint of any Docker file.

Added only when the request asks for deployment. The image runs as a non-root user, pins its base to a minor
version, has a health check, and the compose service drops privileges.
"""

from __future__ import annotations

import re
from pathlib import Path

from prompt_loader import load_prompt

_ASKS_RE = re.compile(r"\b(?:docker\w*|konteyner\w*|container\w*|deploy\w*|yayına\s+al\w*|sunucuya\s+kur\w*)\b", re.IGNORECASE)
_BASE = "python:3.12-slim"

IGNORE = ".git\n.history\n__pycache__\nvenv\n.venv\n.env\n*.db\ntests\n"


def lint(text: str) -> list[str]:
    """Common Dockerfile mistakes."""
    problems = []
    for image in re.findall(r"^FROM\s+(\S+)", text, re.MULTILINE):
        if (":" not in image and "@" not in image and image != "scratch") or image.endswith(":latest"):
            problems.append(f"taban imaj sürümü sabitlenmemiş: {image}")
    users = re.findall(r"^USER\s+(\S+)", text, re.MULTILINE)
    if not users or users[-1] in ("root", "0"):
        problems.append("konteyner root olarak çalışıyor")
    if "HEALTHCHECK" not in text:
        problems.append("sağlık denetimi yok")
    if re.search(r"^(?:ENV|ARG)\s+\w*(?:PASSWORD|SECRET|TOKEN|KEY)\w*[= ]\S+", text, re.MULTILINE | re.IGNORECASE):
        problems.append("imaja gizli değer yazılmış")
    if re.search(r"^ADD\s+https?://", text, re.MULTILINE):
        problems.append("ADD ile uzaktan dosya indiriliyor")
    return problems


def _entry_module(ws_dir: Path) -> str:
    for name in ("main.py", "app.py", "app/main.py", "src/main.py", "backend/app.py"):
        path = ws_dir / name
        if path.is_file() and re.search(r"^app\s*=\s*FastAPI\(", path.read_text(encoding="utf-8", errors="replace"), re.MULTILINE):
            return name[:-3].replace("/", ".")
    return ""


def apply(ws_dir: Path, request: str) -> str:
    """One chat line about the Docker files: added, or what is wrong with the ones already there."""
    existing = ws_dir / "Dockerfile"
    if existing.is_file():
        found = lint(existing.read_text(encoding="utf-8", errors="replace"))
        if not found or not _ASKS_RE.search(request):
            return "Dockerfile denetimi: " + "; ".join(found) if found else ""
    module = _entry_module(ws_dir)
    if not _ASKS_RE.search(request) or not module or not (ws_dir / "requirements.txt").is_file():
        return ""
    requirements = (ws_dir / "requirements.txt").read_text(encoding="utf-8")
    if not re.search(r"^uvicorn\b", requirements, re.MULTILINE):
        (ws_dir / "requirements.txt").write_text(requirements.rstrip("\n") + "\nuvicorn\n", encoding="utf-8")
    existing.write_text(load_prompt("deploy_dockerfile.txt").replace("{base}", _BASE).replace("{module}", module).rstrip("\n") + "\n", encoding="utf-8")
    (ws_dir / "docker-compose.yml").write_text(load_prompt("deploy_compose.yml.txt").rstrip("\n") + "\n", encoding="utf-8")
    (ws_dir / ".dockerignore").write_text(IGNORE, encoding="utf-8")
    return "Dağıtım dosyaları eklendi: Dockerfile (root olmayan kullanıcı, sağlık denetimi), docker-compose.yml (salt okunur, yetkisiz). Çalıştırma: docker compose up --build"
