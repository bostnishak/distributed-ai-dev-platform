"""Cluster D ([M55]): Isolated & Policy-Validated Code Execution Micro-Sandbox.

Validates Python source via AST to block dangerous system/network modules and executes
verified code inside an isolated temporary directory subprocess with strict timeout enforcement.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

_BLOCKED_IMPORTS: set[str] = {
    "socket",
    "subprocess",
    "shutil",
    "ctypes",
    "multiprocessing",
    "webbrowser",
    "ftplib",
    "telnetlib",
    "urllib",
    "http",
    "requests",
    "httpx",
}

_BLOCKED_BUILTINS: set[str] = {"eval", "exec", "compile", "__import__", "open"}


def _inspect_ast_safety(code: str) -> list[str]:
    violations: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"SyntaxError at line {exc.lineno}: {exc.msg}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_mod = alias.name.split(".")[0]
                if root_mod in _BLOCKED_IMPORTS:
                    violations.append(f"Blocked import '{root_mod}' in isolated sandbox")
        elif isinstance(node, ast.ImportFrom):
            root_mod = (node.module or "").split(".")[0]
            if root_mod in _BLOCKED_IMPORTS:
                violations.append(f"Blocked import from '{root_mod}' in isolated sandbox")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _BLOCKED_BUILTINS:
                violations.append(f"Blocked builtin call '{node.func.id}()' in isolated sandbox")
            elif isinstance(node.func, ast.Attribute) and node.func.attr in {"system", "popen", "remove", "unlink", "rmdir"}:
                violations.append(f"Blocked system call '.{node.func.attr}()' in isolated sandbox")

    return violations


def run_in_isolated_sandbox(code: str, timeout_sec: int = 5) -> dict[str, Any]:
    """Validate and run Python ``code`` in an isolated temporary directory subprocess."""
    raw_code = (code or "").strip()
    if not raw_code:
        raise ValueError("code must not be empty")

    violations = _inspect_ast_safety(raw_code)
    if violations:
        return {
            "ok": False,
            "blocked": True,
            "returncode": -1,
            "stdout": "",
            "stderr": "; ".join(violations),
            "violations": violations,
            "duration_ms": 0.0,
        }

    timeout = max(1, min(int(timeout_sec), 30))
    t0 = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="cm6453_sandbox_") as tmp_dir:
        script_path = Path(tmp_dir) / "sandbox_job.py"
        script_path.write_text(raw_code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(script_path)],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return {
                "ok": proc.returncode == 0,
                "blocked": False,
                "returncode": int(proc.returncode),
                "stdout": (proc.stdout or "").strip(),
                "stderr": (proc.stderr or "").strip(),
                "violations": [],
                "duration_ms": elapsed_ms,
            }
        except subprocess.TimeoutExpired:
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return {
                "ok": False,
                "blocked": False,
                "returncode": -9,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds",
                "violations": ["TIMEOUT"],
                "duration_ms": elapsed_ms,
            }


__all__ = ["run_in_isolated_sandbox"]
