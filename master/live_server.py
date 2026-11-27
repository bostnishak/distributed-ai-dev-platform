"""Boot a generated server for real, reachable on one local port, and restart it with its data kept.

The code runs in the hardened container (non-root, no capabilities, memory and process limits) on a copy of the
project; the only difference from the offline sandbox is that its port is published on 127.0.0.1.
"""

from __future__ import annotations

import contextlib
import shutil
import tempfile
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import httpx

import atomic_io
import process_registry
import process_utils
import workspace_docker
import workspace_requirements
import workspace_smoke
from sandbox import runner

_READY_S = 60
_INSIDE = 8000


def _docker(*args: str, timeout_s: int = 60) -> process_utils.ProcessResult:
    exe = shutil.which("docker")
    if not exe:
        raise OSError("docker bulunamadı")
    return process_utils.run_process([exe, *args], timeout_s=timeout_s)


class LiveServer:
    def __init__(self, name: str, port: int) -> None:
        self.name, self.port = name, port
        self.url = f"http://127.0.0.1:{port}"

    def logs(self) -> str:
        done = _docker("logs", "--tail", "30", self.name)
        return (done.stdout + done.stderr)[-1500:]

    def reason(self) -> str:
        """The line of the log that says what went wrong (the last error line, else the last line)."""
        lines = [line.strip() for line in self.logs().splitlines() if line.strip()]
        errors = [line for line in lines if "Error" in line or "Exception" in line]
        return (errors or lines or ["günlük boş"])[-1][:300]

    def alive(self) -> bool:
        return _docker("inspect", "-f", "{{.State.Running}}", self.name).stdout.strip() == "true"

    def wait(self) -> None:
        """Any answer below 500 on /health or / means the server is up."""
        deadline = time.time() + _READY_S
        while time.time() < deadline:
            for path in ("/health", "/"):
                try:
                    if httpx.get(self.url + path, timeout=2).status_code < 500:
                        return
                except httpx.HTTPError:
                    continue
            if _docker("inspect", "-f", "{{.State.Running}}", self.name).stdout.strip() == "false":
                raise OSError(f"sunucu açılırken durdu: {self.reason()}")
            time.sleep(0.5)
        raise OSError(f"sunucu {_READY_S} sn içinde yanıt vermedi: {self.reason()}")

    def restart(self) -> None:
        done = _docker("restart", "-t", "5", self.name)
        if done.returncode != 0:
            raise OSError(f"yeniden başlatılamadı: {done.stderr[-300:]}")
        self.wait()


def _command(ws_dir: Path, entry: Path) -> list[str]:
    module = entry.relative_to(ws_dir).with_suffix("").as_posix().replace("/", ".")
    source = entry.read_text(encoding="utf-8", errors="replace")
    if "FastAPI" in source:
        return ["python", "-m", "uvicorn", f"{module}:app", "--host", "0.0.0.0", "--port", str(_INSIDE)]
    if "Flask" in source:
        return ["python", "-m", "flask", "--app", module, "run", "--host", "0.0.0.0", "--port", str(_INSIDE)]
    raise ValueError("FastAPI ya da Flask giriş noktası bulunamadı")


@contextlib.contextmanager
def serve(ws_dir: Path) -> Iterator[LiveServer]:
    """The running server of a copy of the project; removed afterwards, the project itself is never written to."""
    entry = workspace_smoke._find_entry(ws_dir)
    if entry is None:
        raise ValueError("çalıştırılacak bir sunucu giriş noktası yok")
    command = _command(ws_dir, entry)
    packages = sorted({*workspace_requirements.declared_packages(ws_dir), "uvicorn", "fastapi"} if "uvicorn" in command else {*workspace_requirements.declared_packages(ws_dir), "flask"})
    port = process_registry.lease_port()
    name = f"cm6453-live-{uuid.uuid4().hex[:8]}"
    stage = Path(tempfile.mkdtemp(prefix="cm6453_live_"))
    try:
        workspace_docker._stage(ws_dir, packages, stage)
        args = ["run", "-d", "--name", name, "--user", runner.SANDBOX_UID_GID, "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
                "--memory", "512m", "--cpus", "1", "--pids-limit", "128", "-p", f"127.0.0.1:{port}:{_INSIDE}", "-v", f"{stage.resolve()}:/sandbox", "-w", "/sandbox",
                "-e", "PYTHONPATH=/sandbox/.deps:/sandbox", "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "HOME=/tmp", runner.SANDBOX_IMAGE, *command]
        started = _docker(*args, timeout_s=120)
        if started.returncode != 0:
            raise OSError(f"kap açılamadı: {started.stderr[-300:]}")
        server = LiveServer(name, port)
        server.wait()
        yield server
    finally:
        _docker("rm", "-f", name)
        process_registry.release_port(port)
        with contextlib.suppress(OSError):
            atomic_io.remove_tree(stage)
