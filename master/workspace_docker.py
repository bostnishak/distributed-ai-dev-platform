"""Run a generated project inside the hardened Docker sandbox (no network, no host files, dropped capabilities).

Dependencies are installed in a separate, short-lived container that has network access but only ever sees a
temporary copy of the project; the project code itself then runs in the offline sandbox from `sandbox.runner`.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

from sandbox import runner

_DEPS_ROOT = Path(tempfile.gettempdir()) / "cm6453_sandbox_deps"
_GUI_MARKERS = ("_tkinter", "No module named 'tkinter'", "No module named 'pygame'", "pygame.error", "no display name", "TclError")


def available() -> bool:
    return runner.docker_daemon_ready()[0]


def _pip_install(deps: Path, pkgs: list[str]) -> None:
    """Install allow-listed packages into `deps` from a networked but unprivileged container."""
    if (deps / ".ok").exists() or not pkgs:
        return
    deps.mkdir(parents=True, exist_ok=True)
    args = ["docker", "run", "--rm", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--memory", "768m", "--cpus", "1",
            "--pids-limit", "128", "-v", f"{deps.resolve()}:/deps", "-e", "PIP_DISABLE_PIP_VERSION_CHECK=1", "-e", "HOME=/tmp",
            "--entrypoint", "pip", runner.SANDBOX_IMAGE, "install", "-q", "--no-cache-dir", "--target", "/deps", *pkgs]
    proc = runner._run_docker_cmd(args, timeout_s=300)
    if proc.returncode == 0:
        (deps / ".ok").write_text("ok", encoding="utf-8")


def _stage(ws_dir: Path, pkgs: list[str], stage: Path) -> None:
    shutil.copytree(ws_dir, stage, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".history", "__pycache__", ".git"))
    key = hashlib.sha256("\n".join(sorted(pkgs)).encode()).hexdigest()[:16]
    deps = _DEPS_ROOT / key
    _pip_install(deps, pkgs)
    if deps.is_dir():
        shutil.copytree(deps, stage / ".deps", dirs_exist_ok=True)


def _sandbox_command(command: list[str]) -> list[str]:
    return ["env", "PYTHONPATH=/sandbox/.deps", "PYTHONDONTWRITEBYTECODE=1", "SDL_VIDEODRIVER=dummy", "SDL_AUDIODRIVER=dummy", *command]


def run_probe(ws_dir: Path, entry: Path, probe: str, pkgs: list[str]) -> tuple[bool, str, list[str]]:
    """Same contract as the host probe: (ok, log, routes). A timeout means the app started and kept running."""
    with tempfile.TemporaryDirectory(prefix="cm6453_ws_") as tmp:
        stage = Path(tmp) / "ws"
        _stage(ws_dir, pkgs, stage)
        rel = entry.relative_to(ws_dir).as_posix()
        res = runner.run_workspace_command(stage, _sandbox_command(["python", "-c", probe, f"/sandbox/{rel}"]), read_only_mount=False, timeout_s=40)
    if res["timed_out"]:
        return True, "", []
    if not res["docker_available"]:
        raise OSError(res["stderr"])
    out = res["stdout"]
    routes = json.loads(m.group(1)) if (m := re.search(r"^ROUTES=(.*)$", out, re.M)) else []
    log = (res["stderr"] or out)[-2500:]
    if "SMOKE_OK" not in out and any(mark in log for mark in _GUI_MARKERS):
        return True, "", routes  # desktop/GUI libraries cannot open a window here; they are checked statically instead
    return "SMOKE_OK" in out, log, routes


def run_tests(ws_dir: Path, pkgs: list[str]) -> str:
    """The project's own pytest run inside the sandbox; returns the last output line on failure, else ''."""
    with tempfile.TemporaryDirectory(prefix="cm6453_ws_") as tmp:
        stage = Path(tmp) / "ws"
        _stage(ws_dir, pkgs, stage)
        res = runner.run_workspace_command(stage, _sandbox_command(["python", "-m", "pytest", "-x", "-q", "--no-header", "-p", "no:cacheprovider"]), read_only_mount=False, timeout_s=60)
    if res["timed_out"] or res["ok"]:
        return ""
    return (res["stdout"].strip().splitlines() or ["test başarısız"])[-1]
