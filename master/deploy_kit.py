"""Hardened Docker files for a generated Python web project, written by code, plus a lint of any Docker file.

Added only when the request asks for deployment. The image runs as a non-root user, pins its base to a minor
version, has a health check, and the compose service drops privileges.
"""

from __future__ import annotations

import re
from pathlib import Path

_ASKS_RE = re.compile(r"\b(?:docker\w*|konteyner\w*|container\w*|deploy\w*|yayına\s+al\w*|sunucuya\s+kur\w*)\b", re.IGNORECASE)
_BASE = "python:3.12-slim"

DOCKERFILE = """FROM {base} AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --target /deps -r requirements.txt

FROM {base}
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
WORKDIR /app
COPY --from=build /deps /deps
COPY --chown=app:app . .
ENV PYTHONPATH=/deps PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/openapi.json')"
CMD ["python", "-m", "uvicorn", "{module}:app", "--host", "0.0.0.0", "--port", "8000"]
"""

COMPOSE = """services:
  web:
    build: .
    ports:
      - "127.0.0.1:8000:8000"
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      - data:/app/data
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    mem_limit: 512m
    restart: unless-stopped
volumes:
  data:
"""

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
    existing.write_text(DOCKERFILE.format(base=_BASE, module=module), encoding="utf-8")
    (ws_dir / "docker-compose.yml").write_text(COMPOSE, encoding="utf-8")
    (ws_dir / ".dockerignore").write_text(IGNORE, encoding="utf-8")
    return "Dağıtım dosyaları eklendi: Dockerfile (root olmayan kullanıcı, sağlık denetimi), docker-compose.yml (salt okunur, yetkisiz). Çalıştırma: docker compose up --build"
