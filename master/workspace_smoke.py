"""Run a freshly generated Python project once in a throw-away environment and let the model repair what crashes.

The check imports the entry module (and, for Flask apps, requests "/"), so missing templates, bad imports and
crashes at start-up are caught before the user downloads the ZIP.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
import tempfile
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any

from process_utils import run_process
from workspace_contract import contract_problem
from workspace_requirements import repair_project

_PROBE = (Path(__file__).parent / "prompts" / "smoke_probe.py.txt").read_text(encoding="utf-8")
_FRAME_RE = re.compile(r'File "([^"]+)", line (\d+)')
_ENTRIES = ("run.py", "app.py", "main.py", "backend/app.py", "src/main.py", "app/main.py")
_Regenerate = Callable[[str, str], Awaitable[str]]


def _sandbox_python() -> Path:
    venv = Path(tempfile.gettempdir()) / "cm6453_sandbox_venv"
    py = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not py.exists():
        run_process([sys.executable, "-m", "venv", str(venv)], timeout_s=180)
    return py


def _find_entry(ws_dir: Path) -> Path | None:
    return next((ws_dir / e for e in _ENTRIES if (ws_dir / e).is_file()), None)


def _run_probe(ws_dir: Path, entry: Path) -> tuple[bool, str, list[str]]:
    py = _sandbox_python()
    req = ws_dir / "requirements.txt"
    pkgs = [ln.strip() for ln in req.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")] if req.is_file() else []
    if pkgs:
        run_process([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", *pkgs], timeout_s=300)
    proc = run_process([str(py), "-c", _PROBE, str(entry)], cwd=ws_dir, timeout_s=25, max_output_chars=2500)
    if proc.timed_out:
        return True, "", []  # long-running app (server/GUI loop): it started, which is what we wanted to know
    routes = json.loads(m.group(1)) if (m := re.search(r"^ROUTES=(.*)$", proc.stdout, re.M)) else []
    return "SMOKE_OK" in proc.stdout, (proc.stderr or proc.stdout)[-2500:], routes


def _diagnose(ws_dir: Path, ok: bool, log: str, routes: list[str]) -> tuple[bool, Path | None, str]:
    """(passed, file to repair, error text) for one probe run."""
    if not ok:
        return False, _failing_file(ws_dir, log), log
    problem = contract_problem(ws_dir, routes)
    return (True, None, "") if problem is None else (False, problem[0], problem[1])


def _failing_file(ws_dir: Path, log: str) -> Path | None:
    root = ws_dir.resolve()
    for raw, _line in reversed(_FRAME_RE.findall(log)):
        p = Path(raw)
        if p.is_file() and root in p.resolve().parents and ".history" not in p.parts:
            return p
    return None


def _repair_prompt(ws_dir: Path, target: Path, log: str) -> tuple[str, str]:
    rel = target.relative_to(ws_dir.resolve()).as_posix()
    body = target.read_text(encoding="utf-8", errors="replace")
    return rel, (
        f"`{rel}` dosyası çalıştırılırken şu hata oluştu:\n{log}\n\nMevcut içerik:\n{body}\n\n"
        "Hatayı düzelt ve dosyanın eksiksiz içeriğini döndür. Diğer dosyalarla uyumlu kal."
    )


def _apply_fix(target: Path, fixed: str, ws_dir: Path) -> None:
    if fixed.strip():
        target.write_text(re.sub(r"^```\w*\n|\n```\s*$", "", fixed.strip()), encoding="utf-8")
    repair_project(ws_dir)


async def smoke_and_repair(ws_dir: Path, regenerate: _Regenerate, rounds: int = 2) -> AsyncIterator[dict[str, Any]]:
    """Yield status events; the last event is {"type": "smoke", "ok": bool, "warning": str}."""
    ws_dir = await asyncio.to_thread(ws_dir.resolve)
    entry = _find_entry(ws_dir)
    if entry is None:
        yield {"type": "smoke", "ok": True, "warning": ""}
        return
    log = ""
    for attempt in range(rounds + 1):
        yield {"type": "status", "message": "Proje çalıştırılarak test ediliyor..." if attempt == 0 else f"Hata düzeltildi, yeniden test ediliyor ({attempt}/{rounds})..."}
        try:
            ok, log, routes = await asyncio.to_thread(_run_probe, ws_dir, entry)
        except (OSError, subprocess.SubprocessError) as exc:
            yield {"type": "smoke", "ok": True, "warning": f"Otomatik test çalıştırılamadı: {exc}"}
            return
        passed, target, log = _diagnose(ws_dir, ok, log, routes)
        if passed:
            yield {"type": "smoke", "ok": True, "warning": ""}
            return
        if attempt == rounds or target is None:
            break
        rel, ask = _repair_prompt(ws_dir, target, log)
        _apply_fix(target, await regenerate(rel, ask), ws_dir)
    yield {"type": "smoke", "ok": False, "warning": "Otomatik çalıştırma testi hata verdi: " + (log.strip().splitlines() or ["bilinmeyen hata"])[-1][:200]}
