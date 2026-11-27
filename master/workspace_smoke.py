"""Run a freshly generated Python project once in a throw-away environment and let the model repair what crashes.

The check imports the entry module (and, for Flask apps, requests "/"), so missing templates, bad imports and
crashes at start-up are caught before the user downloads the ZIP.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any

import causal_debug
import cheat_guard
import complexity_governor
import debug_probe
import spec_contract
import workspace_behavior
import workspace_docker
import workspace_node
import workspace_web
from process_utils import run_process
from prompt_loader import load_prompt
from workspace_checks import extract_file, static_problem
from workspace_contract import contract_problem
from workspace_requirements import _PIP_NAMES, repair_project

_PROBE = "".join((Path(__file__).parent / "prompts" / name).read_text(encoding="utf-8") for name in ("api_probe.py.txt", "smoke_probe.py.txt"))
_FRAME_RE = re.compile(r'File "([^"]+)", line (\d+)')
_ENTRIES = ("run.py", "app.py", "main.py", "backend/app.py", "src/main.py", "app/main.py")
_Regenerate = Callable[[str, str], Awaitable[str]]


def _sandbox_python() -> Path:
    venv = Path(tempfile.gettempdir()) / "cm6453_sandbox_venv"
    py = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not py.exists():
        run_process([sys.executable, "-m", "venv", str(venv)], timeout_s=180)
    return py


_SAFE_PACKAGES = {n.lower() for n in _PIP_NAMES.values()} | {"greenlet", "aiosqlite", "sqlalchemy", "requests", "numpy", "pandas", "matplotlib", "pytest", "httpx", "jinja2", "werkzeug", "gunicorn", "click"}


def _clean_env() -> dict[str, str]:
    """Generated code runs with a minimal environment: no API keys, tokens or other secrets of this server."""
    keep = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "COMSPEC", "PATHEXT", "WINDIR", "LANG")
    return {k: v for k, v in os.environ.items() if k.upper() in keep}


def _find_entry(ws_dir: Path) -> Path | None:
    return next((ws_dir / e for e in _ENTRIES if (ws_dir / e).is_file()), None)


def _safe_requirements(ws_dir: Path) -> list[str]:
    req = ws_dir / "requirements.txt"
    pkgs = [ln.strip() for ln in req.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")] if req.is_file() else []
    return [p for p in pkgs if re.split(r"[<>=!~\[; ]", p, maxsplit=1)[0].lower() in _SAFE_PACKAGES]  # never install unknown names


def _run_node_probe(ws_dir: Path) -> tuple[bool, str, list[str]]:
    node_entry = workspace_node.find_entry(ws_dir)
    if node_entry is None or not workspace_docker.available():
        return True, "", []  # nothing runnable here, or no sandbox: static checks still apply
    ok, log = workspace_node.run_probe(ws_dir, node_entry)
    return ok, log, []


def _run_probe(ws_dir: Path, entry: Path) -> tuple[bool, str, list[str]]:
    pkgs = _safe_requirements(ws_dir)
    if any(p.lower().startswith("fastapi") for p in pkgs) and "httpx" not in pkgs:
        pkgs.append("httpx")  # FastAPI's test client needs it
    if workspace_docker.available():
        return workspace_docker.run_probe(ws_dir, entry, _PROBE, pkgs)
    py = _sandbox_python()
    if pkgs:
        run_process([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", *pkgs], timeout_s=300)
    proc = run_process([str(py), "-c", _PROBE, str(entry)], cwd=ws_dir, timeout_s=25, max_output_chars=2500, env=_clean_env())
    if proc.timed_out:
        return True, "", []  # long-running app (server/GUI loop): it started, which is what we wanted to know
    routes = json.loads(m.group(1)) if (m := re.search(r"^ROUTES=(.*)$", proc.stdout, re.M)) else []
    return "SMOKE_OK" in proc.stdout, (proc.stderr or proc.stdout)[-2500:], routes


def _tests_log(ws_dir: Path) -> str:
    """Run the project's own tests once; '' when they pass or there are none, else the end of the output."""
    tests = ws_dir / "tests"
    if not tests.is_dir() or not any(tests.glob("test_*.py")):
        return ""
    if workspace_docker.available():
        return workspace_docker.test_log(ws_dir, _safe_requirements(ws_dir))
    py = _sandbox_python()
    run_process([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", "pytest"], timeout_s=180)
    proc = run_process([str(py), "-m", "pytest", "-x", "-q", "--no-header", "-p", "no:cacheprovider"], cwd=ws_dir, timeout_s=60, max_output_chars=3000, env=_clean_env())
    if proc.timed_out or proc.returncode == 0:
        return ""
    return proc.stdout.strip()[-3000:] or "test başarısız"


def _tests_with_state(ws_dir: Path) -> str:
    """The failing test output plus what the debugger saw at the moment of the exception."""
    log = _tests_log(ws_dir)
    if not log:
        return ""
    state = debug_probe.describe(debug_probe.inspect(ws_dir, _safe_requirements(ws_dir)))
    return f"{log}\n\n{state}" if state else log


def _diagnose(ws_dir: Path, ok: bool, log: str, routes: list[str]) -> tuple[bool, Path | None, str]:
    """(passed, file to repair, error text) for one probe run."""
    if not ok:
        return False, _failing_file(ws_dir, log), log
    problem = contract_problem(ws_dir, routes) or static_problem(ws_dir)
    return (True, None, "") if problem is None else (False, problem[0], problem[1])


def _failing_file(ws_dir: Path, log: str) -> Path | None:
    root = ws_dir.resolve()
    if (node_file := workspace_node.failing_file(root, log)) is not None:
        return node_file
    for raw, _line in reversed(_FRAME_RE.findall(log)):
        p = root / raw.removeprefix("/sandbox/") if raw.startswith("/sandbox/") else Path(raw)  # container paths map back to the host copy
        if p.is_file() and root in p.resolve().parents and ".history" not in p.parts:
            return p
    return None


def _repair_prompt(ws_dir: Path, target: Path, log: str) -> tuple[str, str]:
    rel = target.relative_to(ws_dir.resolve()).as_posix()
    body = target.read_text(encoding="utf-8", errors="replace")
    return rel, (
        load_prompt("agent_qa.md") + "\n"
        f"`{rel}` dosyası çalıştırılırken şu hata oluştu:\n{log}\n\nMevcut içerik:\n{body}\n\n"
        "Hatayı düzelt ve dosyanın eksiksiz içeriğini döndür. Diğer dosyalarla uyumlu kal."
    )


def _apply_fix(target: Path, fixed: str, ws_dir: Path) -> None:
    """Write the repaired file; a reply with several files or stray prose is reduced to the one block that belongs to `target`."""
    before = target.read_text(encoding="utf-8", errors="replace")
    old = before.lower()
    if (body := extract_file(fixed, target.suffix)) and ("</html>" not in old or "</html>" in body.lower()):  # never save a cut-off page
        relative = target.relative_to(ws_dir).as_posix()
        tests = {p.name: p.read_text(encoding="utf-8", errors="replace") for p in ws_dir.rglob("test_*.py")}
        if violations := cheat_guard.review(relative, before, body, cheat_guard.test_literals(tests)):
            cheat_guard.record(violations)  # a repair that games the checks is thrown away
        else:
            target.write_text(body, encoding="utf-8")
    repair_project(ws_dir)


async def _scenario_problem(ws_dir: Path, request: str, regenerate: _Regenerate, cache: list[Any]) -> tuple[Path | None, str] | None:
    """(file, text) when a user scenario written from the request fails on the real page; the scenarios are written once (cache[0])."""
    if not request or not workspace_web.has_page(ws_dir) or not workspace_docker.available():
        return None
    if not cache:
        cache.append(await workspace_behavior.tests_for(request, ws_dir, regenerate))
    failures = await asyncio.to_thread(workspace_behavior.run, ws_dir, cache[0]) if cache[0] else []
    return workspace_behavior.problem(ws_dir, failures) if failures else None


async def smoke_and_repair(ws_dir: Path, regenerate: _Regenerate, rounds: int = 2, request: str = "") -> AsyncIterator[dict[str, Any]]:
    """Yield status events; the last event is {"type": "smoke", "ok": bool, "warning": str}."""
    ws_dir = await asyncio.to_thread(ws_dir.resolve)
    entry = _find_entry(ws_dir)
    log = ""
    scenarios: list[Any] = []
    for attempt in range(rounds + 1):
        yield {"type": "status", "message": "Proje çalıştırılarak test ediliyor..." if attempt == 0 else f"Hata düzeltildi, yeniden test ediliyor ({attempt}/{rounds})..."}
        try:
            ok, log, routes = await asyncio.to_thread(_run_probe, ws_dir, entry) if entry else await asyncio.to_thread(_run_node_probe, ws_dir)
        except (OSError, subprocess.SubprocessError) as exc:
            yield {"type": "smoke", "ok": True, "warning": f"Otomatik test çalıştırılamadı: {exc}"}
            return
        passed, target, log = _diagnose(ws_dir, ok, log, routes)
        if passed and workspace_web.has_page(ws_dir) and workspace_docker.available():
            result = await asyncio.to_thread(workspace_web.probe, ws_dir)  # real page load + clicks in jsdom
            if result and (found := workspace_web.problem(ws_dir, result) or spec_contract.problem(ws_dir, request)):
                passed, target, log = False, found[0], found[1]
            elif result and (scenario := await _scenario_problem(ws_dir, request, regenerate, scenarios)):
                passed, target, log = False, scenario[0], scenario[1]
        if passed:
            yield {"type": "status", "message": "Projenin kendi testleri çalıştırılıyor..."}
            _ok, test_warning = await causal_debug.repair(ws_dir, lambda: _tests_with_state(ws_dir), regenerate) if entry else (True, "")
            if not _ok and complexity_governor.classify(request).level >= 3 and workspace_docker.available():
                yield {"type": "status", "message": "Farklı düzeltme yolları aranıyor..."}
                _ok, searched = await causal_debug.explore(ws_dir, lambda: workspace_docker.test_log(ws_dir, _safe_requirements(ws_dir), ("--maxfail=50",)), regenerate)
                test_warning = searched if _ok else f"{test_warning} {searched}"
            yield {"type": "smoke", "ok": True, "warning": test_warning}
            return
        if attempt == rounds or target is None:
            break
        rel, ask = _repair_prompt(ws_dir, target, log)
        _apply_fix(target, await regenerate(rel, ask), ws_dir)
    yield {"type": "smoke", "ok": False, "warning": "Otomatik çalıştırma testi hata verdi: " + (log.strip().splitlines() or ["bilinmeyen hata"])[-1][:200]}
