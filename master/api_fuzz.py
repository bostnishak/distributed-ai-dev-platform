"""Throw bad input at a generated API inside the offline sandbox: empty, huge, hostile, broken and simultaneous requests.

What is reported: any 5xx (the code did not handle it), a script echoed back unescaped, and very slow answers.
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
from pathlib import Path

import workspace_docker
import workspace_requirements
import workspace_smoke
from prompt_loader import load_prompt

_log = logging.getLogger(__name__)


def run(ws_dir: Path) -> dict | None:
    """{"requests": n, "findings": [...]}; None when there is no FastAPI entry or no sandbox."""
    entry = workspace_smoke._find_entry(ws_dir)
    if entry is None or "FastAPI" not in entry.read_text(encoding="utf-8", errors="replace") or not workspace_docker.available():
        return None
    packages = sorted({*workspace_requirements.declared_packages(ws_dir), "fastapi", "httpx"})
    with tempfile.TemporaryDirectory(prefix="cm6453_fuzz_", ignore_cleanup_errors=True) as tmp:
        stage = Path(tmp) / "ws"
        workspace_docker._stage(ws_dir, packages, stage)
        command = ["python", "-c", load_prompt("api_fuzz.py.txt"), f"/sandbox/{entry.relative_to(ws_dir).as_posix()}"]
        result = workspace_docker.runner.run_workspace_command(stage, workspace_docker._sandbox_command(command), read_only_mount=False, timeout_s=90)
    found = re.search(r"^RESULT=(.*)$", result["stdout"], re.MULTILINE)
    if not found:
        _log.warning("fuzzing could not run: %s", (result["stderr"] or result["stdout"])[-300:])
        return None
    return json.loads(found.group(1))


def report(ws_dir: Path) -> str:
    """One warning line, or '' when everything was handled or there is no API."""
    outcome = run(ws_dir)
    if not outcome or not outcome["findings"]:
        return ""
    return f"API zorlama testi ({outcome['requests']} istek) sorun buldu: " + "; ".join(outcome["findings"][:3])
