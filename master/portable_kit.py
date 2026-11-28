"""One-click start kit for an exported project, and a test that the exported ZIP really runs.

The ZIP gets run_windows.bat, run.ps1, a launcher, pinned dependencies and hardened Docker files (only those the
project does not already have). The test unpacks the ZIP into an empty folder and boots that copy: in Docker for
generated code (it never runs on the host unsandboxed), through the kit's own script only when the caller trusts it.

  paketi sına                 unpacks the last project's ZIP and boots it in a container
"""

from __future__ import annotations

import asyncio
import importlib.metadata
import io
import logging
import re
import tempfile
import time
import uuid
import zipfile
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import httpx
from fastapi.responses import StreamingResponse

import deploy_kit
import live_server
import process_registry
import workspace_builder as wb
import workspace_docker
import workspace_requirements
import workspace_smoke
from process_utils import run_process
from prompt_loader import load_prompt

_PORT = 8000
_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(.*)$")
_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class App:
    kind: str  # "fastapi" | "flask" | "sayfa"
    command: tuple[str, ...]


def detect(ws_dir: Path) -> App | None:
    entry = workspace_smoke._find_entry(ws_dir)
    if entry is not None:
        module = entry.relative_to(ws_dir).with_suffix("").as_posix().replace("/", ".")
        source = entry.read_text(encoding="utf-8", errors="replace")
        if "FastAPI(" in source:
            return App("fastapi", ("-m", "uvicorn", f"{module}:app", "--host", "127.0.0.1", "--port", "{port}"))
        if "Flask(" in source:
            return App("flask", ("-m", "flask", "--app", module, "run", "--host", "127.0.0.1", "--port", "{port}"))
    if (ws_dir / "index.html").is_file():
        return App("sayfa", ("-m", "http.server", "{port}", "--bind", "127.0.0.1"))
    return None


def locked(ws_dir: Path, app: App) -> str:
    """Pinned requirements: a version already written stays; otherwise the version installed here; unknown ones stay open."""
    written = (ws_dir / "requirements.txt").read_text(encoding="utf-8", errors="replace").splitlines() if (ws_dir / "requirements.txt").is_file() else []
    needed = {"fastapi": ["fastapi", "uvicorn"], "flask": ["flask"], "sayfa": []}[app.kind]
    wanted = [line for line in written if line.strip() and not line.lstrip().startswith(("#", "-"))]
    if app.kind != "sayfa":
        wanted = wanted or [p for p in workspace_requirements.declared_packages(ws_dir) if p != "pytest"]
        wanted += [p for p in needed if not any(re.match(rf"{p}\b", line.strip(), re.IGNORECASE) for line in wanted)]
    pinned = []
    for line in wanted:
        match = _NAME_RE.match(line)
        if not match or match[3].strip():
            pinned.append(line.strip())
            continue
        try:
            pinned.append(f"{match[1]}{match[2] or ''}=={importlib.metadata.version(match[1])}")
        except importlib.metadata.PackageNotFoundError:
            pinned.append(line.strip())
    return "\n".join(pinned) + "\n" if pinned else ""


def _docker_files(app: App) -> dict[str, str]:
    if app.kind == "sayfa":
        docker = load_prompt("kit_static_dockerfile.txt")
    else:
        command = " ".join(("python", *app.command)).replace("{port}", "8000").replace("127.0.0.1", "0.0.0.0")
        started = f'CMD ["sh", "-c", "cp -r /app/. /data/ && exec {command}"]'
        docker = load_prompt("deploy_dockerfile.txt").replace("{base}", deploy_kit._BASE)
        docker = re.sub(r"^CMD \[.*\]$", lambda _m: started, docker, flags=re.MULTILINE).replace("COPY requirements.txt .", "COPY requirements.lock requirements.txt")
        if app.kind == "flask":
            docker = docker.replace("/openapi.json", "/")
    return {"Dockerfile": docker.rstrip("\n") + "\n", "docker-compose.yml": load_prompt("deploy_compose.yml.txt").rstrip("\n") + "\n", ".dockerignore": deploy_kit.IGNORE}


def files(ws_dir: Path) -> dict[str, bytes]:
    """The kit files the project does not have yet; {} when there is nothing to start."""
    app = detect(ws_dir)
    if app is None:
        return {}
    launcher = load_prompt("kit_launcher.py.txt").replace("__COMMAND__", repr(list(app.command))).replace("__PORT__", str(_PORT))
    lock = locked(ws_dir, app)
    made = {
        "start_app.py": launcher.encode("utf-8"),
        "run.ps1": load_prompt("kit_run.ps1.txt").replace("__PORT__", str(_PORT)).replace("\n", "\r\n").encode("utf-8-sig"),
        "run_windows.bat": load_prompt("kit_run_windows.bat.txt").replace("\r\n", "\n").replace("\n", "\r\n").encode("ascii"),
        **({"requirements.lock": lock.encode("utf-8")} if lock or app.kind != "sayfa" else {}),
        **{name: text.encode("utf-8") for name, text in _docker_files(app).items()},
    }
    return {name: data for name, data in made.items() if not (ws_dir / name).exists()}


def archive(ws_dir: Path, root: str) -> bytes:
    """The project as the user downloads it, kit included, under one top folder."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target:
        for rel_dir in wb.list_relative_dirs(ws_dir):
            target.writestr(zipfile.ZipInfo(f"{root}/{rel_dir}/"), b"")
        for rel in wb.list_relative_files(ws_dir):
            target.write(ws_dir / rel, arcname=f"{root}/{rel}")
        for name, data in files(ws_dir).items():
            target.writestr(f"{root}/{name}", data)
    return buffer.getvalue()


def unpack(data: bytes, folder: Path) -> Path:
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        source.extractall(folder)
    return next(p for p in folder.iterdir() if p.is_dir())


def _answers(url: str, wait_s: float) -> bool:
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        try:
            return httpx.get(url, timeout=3).status_code < 500
        except httpx.HTTPError:
            time.sleep(0.7)
    return False


def docker_test(ws_dir: Path) -> tuple[bool, str]:
    """Builds the image from the exported copy alone and checks that it answers; (passed, detail)."""
    if not workspace_docker.available():
        return False, "Docker çalışmıyor; dışa aktarılan paket denenemedi"
    if detect(ws_dir) is None:
        return False, "başlatılacak bir uygulama yok"
    name, port = f"cm6453-export-{uuid.uuid4().hex[:8]}", process_registry.lease_port()
    try:
        with tempfile.TemporaryDirectory(prefix="cm6453_export_", ignore_cleanup_errors=True) as tmp:
            copy = unpack(archive(ws_dir, "paket"), Path(tmp))
            built = run_process(["docker", "build", "-q", "--label", "cm6453=export", "-t", name, str(copy)], timeout_s=600)
            if built.returncode != 0:
                return False, f"imaj kurulamadı: {(built.stderr or built.stdout)[-300:]}"
            started = live_server._docker("run", "-d", "--name", name, "--memory", "512m", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
                                          "-p", f"127.0.0.1:{port}:8000", name)
            if started.returncode != 0:
                return False, f"kap açılamadı: {started.stderr[-200:]}"
            if not _answers(f"http://127.0.0.1:{port}/", 60):
                return False, f"paket yanıt vermedi: {live_server._docker('logs', '--tail', '15', name).stderr[-300:]}"
            return True, "ZIP boş klasöre açıldı, kendi Dockerfile'ıyla kuruldu ve yanıt verdi"
    finally:
        live_server._docker("rm", "-f", name)
        run_process(["docker", "rmi", "-f", name], timeout_s=60)
        process_registry.release_port(port)


_COMMAND_RE = re.compile(r"^\s*paketi\s+(?:sına|test\s+et|dene)\s*[.!]?\s*$", re.IGNORECASE)


async def _stream(ws_id: str) -> AsyncIterator[str]:
    import assistant_stream_fastpaths as fp

    yield fp.sse_event({"type": "status", "message": "Dışa aktarım paketi boş klasöre açılıp kapta başlatılıyor (birkaç dakika sürebilir)..."})
    try:
        passed, detail = await asyncio.to_thread(docker_test, wb.safe_workspace_dir(ws_id))
    except (OSError, ValueError, RuntimeError, httpx.HTTPError) as exc:
        passed, detail = False, f"{type(exc).__name__}: {exc}"
    yield fp.sse_event({"type": "token", "content": f"{'Paket denemesi GEÇTİ' if passed else 'Paket denemesi KALDI'}: {detail}"})
    yield fp.sse_event({"type": "done", "model": "paket", "task_type": "proje"})


def fastpath(prompt: str, history: str) -> StreamingResponse | None:
    if not _COMMAND_RE.match(prompt):
        return None
    import revise_chat

    ws_id = revise_chat.last_workspace_id(history)
    return StreamingResponse(_stream(ws_id), media_type="text/event-stream") if ws_id else None
