"""What the program's variables held when a test failed, read through the Debug Adapter Protocol in the sandbox."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import workspace_docker
from process_utils import run_process
from prompt_loader import load_prompt

_log = logging.getLogger(__name__)


def _tests(ws_dir: Path) -> list[str]:
    folder = ws_dir / "tests"
    return [p.relative_to(ws_dir).as_posix() for p in sorted(folder.glob("test_*.py"))] if folder.is_dir() else []


def inspect(ws_dir: Path, pkgs: list[str], stop_at: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """{"exception", "frames": [{file, line, function, locals}]} for the first failing test, or for the first time
    the conditional breakpoint `stop_at` ({file, line, condition}) is hit; None when not available."""
    tests = _tests(ws_dir)
    if not tests or not workspace_docker.available():
        return None
    try:
        with tempfile.TemporaryDirectory(prefix="cm6453_dap_") as tmp:
            stage = Path(tmp) / "ws"
            workspace_docker._stage(ws_dir, sorted({*pkgs, "debugpy"}), stage)
            shutil.rmtree(stage / ".history", ignore_errors=True)
            # same hardening as the web probe (no network, no capabilities); a debugger needs more threads than the code runner allows
            command = ["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--memory", "768m",
                       "--cpus", "2", "--pids-limit", "256", "-v", f"{stage.resolve()}:/sandbox", "-w", "/sandbox", "-e", "HOME=/tmp",
                       "-e", "PYTHONPATH=/sandbox/.deps", "--entrypoint", "python", workspace_docker.runner.SANDBOX_IMAGE,
                       "-c", load_prompt("dap_probe.py.txt"), "/sandbox", *([f"--break={json.dumps(stop_at)}"] if stop_at else []), *tests]
            res = run_process(command, timeout_s=90)
    except (OSError, subprocess.SubprocessError) as exc:
        _log.warning("debugger could not run: %r", exc)
        return None
    found = re.search(r"^RESULT=(.*)$", res.stdout, re.MULTILINE)
    if not found:
        _log.warning("debugger gave no result: %s", res.stderr[-300:])
        return None
    data = json.loads(found.group(1))
    return data if data["exception"] or stop_at else None


_BREAK_RE = re.compile(r"^\s*(?:koşullu\s+)?kesme(?:\s+noktası)?\s*:?\s+(?P<file>[\w./-]+\.py):(?P<line>\d{1,6})(?:\s+(?:koşul\s*:?\s*)?(?P<condition>.{1,120}?))?\s*$", re.IGNORECASE)


def asked(prompt: str) -> dict[str, Any] | None:
    """"koşullu kesme: hesap.py:12 x > 5" as {file, line, condition}."""
    match = _BREAK_RE.match(prompt)
    if not match or ".." in match["file"] or match["file"].startswith("/"):
        return None
    return {"file": match["file"], "line": int(match["line"]), "condition": (match["condition"] or "").strip()}


def explain(ws_dir: Path, pkgs: list[str], stop_at: dict[str, Any], run=inspect) -> str:
    """Run the project's tests under the debugger and report the variables where the breakpoint stopped."""
    where = f"`{stop_at['file']}:{stop_at['line']}`" + (f" (koşul `{stop_at['condition']}`)" if stop_at["condition"] else "")
    if not (ws_dir / stop_at["file"]).is_file():
        return f"Projede `{stop_at['file']}` yok."
    data = run(ws_dir, pkgs, stop_at)
    if data is None:
        return "Hata ayıklayıcı çalıştırılamadı (test dosyası ya da yalıtılmış kutu yok)."
    if data["exception"] != "kesme noktası":
        return f"{where}: testler koşarken bu noktada durulmadı" + (f"; bunun yerine istisna oluştu: {data['exception']}" if data["exception"] else " (koşul hiç sağlanmadı ya da satır çalışmadı).")
    lines = [f"- {f['file']}:{f['line']} {f['function']}() — {', '.join(f'{k}={v}' for k, v in f['locals'].items()) or 'yerel değişken yok'}" for f in data["frames"][:5]]
    return f"{where} kesme noktasında durdu:\n" + "\n".join(lines)


def describe(data: dict[str, Any] | None) -> str:
    """The stopped state as text a repair can use ('' when there is none)."""
    if not data:
        return ""
    lines = [f"HATA AYIKLAYICI (istisna anındaki durum): {data['exception']}"]
    for frame in data["frames"][:6]:
        values = ", ".join(f"{name}={value}" for name, value in frame["locals"].items())
        lines.append(f"- {frame['file']}:{frame['line']} {frame['function']}() — {values or 'yerel değişken yok'}")
    return "\n".join(lines)
