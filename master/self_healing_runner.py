from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

from code_graph import IGNORED_DIRS, build_workspace_code_graph
from process_utils import run_process

SCANNABLE_EXTENSIONS = {".py", ".js", ".ts", ".html", ".sql", ".json", ".env", ".yaml", ".yml"}

_SQL_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"""(?:execute|executemany|raw|query)\s*\(\s*f['"](?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER)\b""",
        re.IGNORECASE,
    ),
    re.compile(
        r"""(?:SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+[^;\n]*['"]\s*\+\s*[A-Za-z_][\w.]*""",
        re.IGNORECASE,
    ),
    re.compile(
        r"""f['"](?:SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b[^'"]*\{[^}]+\}""",
        re.IGNORECASE,
    ),
    re.compile(
        r"""['"](?:SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b[^'"]*%s[^'"]*['"]\s*%\s*""",
        re.IGNORECASE,
    ),
    re.compile(
        r"""['"](?:SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b[^'"]*\{[^}]*\}['"]\.format\s*\(""",
        re.IGNORECASE,
    ),
]

_XSS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"""\.innerHTML\s*\+?=\s*(?!['"`]\s*['"`])(?!['"][^'"{}$]*['"]\s*;)""",
    ),
    re.compile(
        r"""\.outerHTML\s*\+?=\s*(?!['"`]\s*['"`])""",
    ),
    re.compile(
        r"""document\.write\s*\(""",
    ),
    re.compile(
        r"""dangerouslySetInnerHTML\s*=\s*\{""",
    ),
]

_PATH_TRAVERSAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"""(?:open|read_text|read_bytes|write_text|write_bytes|send_file)\s*\([^)\n]*\.\.[/\\]""",
    ),
    re.compile(
        r"""\.\./\.\./""",
    ),
]

_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "Hardcoded API Key / Token",
        re.compile(
            r"""(?i)\b(?:api_key|apikey|secret_key|client_secret|access_token|auth_token|private_key|jwt_secret|password|passwd|db_password)\b\s*[:=]\s*['"](?!change_me|your_|<|none|null|test|dummy|example|placeholder)[A-Za-z0-9_\-/@#!$%^&*+=]{8,}['"]"""
        ),
    ),
    (
        "OpenAI / Bearer Style Key",
        re.compile(r"""\b(?:sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b"""),
    ),
    (
        "PEM Private Key Block",
        re.compile(r"""-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"""),
    ),
]

_UNSAFE_EXEC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"""(?<![.\w])(?:eval|exec)\s*\("""),
    re.compile(r"""subprocess\.(?:Popen|run|call|check_output)\s*\([^)]*shell\s*=\s*True"""),
    re.compile(r"""os\.system\s*\("""),
    re.compile(r"""pickle\.loads?\s*\("""),
]


def _scan_python_ast_security(source: str, rel_path: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError:
        return issues

    has_resolve_check = ".resolve(" in source or "os.path.realpath" in source

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name in {"eval", "exec"}:
                issues.append(
                    {
                        "category": "UNSAFE_EVAL_EXEC",
                        "severity": "CRITICAL",
                        "file": rel_path,
                        "line": getattr(node, "lineno", 1),
                        "message": f"Dynamic code execution via `{func_name}()` detected.",
                        "recommendation": "Replace `eval`/`exec` with `ast.literal_eval`, explicit dispatch tables, or JSON parsing.",
                    }
                )

            if func_name in {"open", "Path"} and node.args and not has_resolve_check:
                first_arg = node.args[0]
                if isinstance(first_arg, (ast.JoinedStr, ast.BinOp)):
                    issues.append(
                        {
                            "category": "PATH_TRAVERSAL",
                            "severity": "HIGH",
                            "file": rel_path,
                            "line": getattr(node, "lineno", 1),
                            "message": f"Dynamic file path passed to `{func_name}()` without `.resolve()` boundary verification.",
                            "recommendation": "Resolve target path with `Path(base, user_input).resolve()` and verify `.is_relative_to(base.resolve())`.",
                        }
                    )

    return issues


class _IssueCollector:
    def __init__(self) -> None:
        self.issues: list[dict[str, Any]] = []
        self._seen: set[tuple[str, str, int]] = set()

    def add(self, issue: dict[str, Any]) -> None:
        key = (issue["category"], issue["file"], issue["line"])
        if key in self._seen:
            return
        self._seen.add(key)
        self.issues.append(issue)


def _scan_line_patterns(
    line: str,
    rel_path: str,
    line_no: int,
    has_resolve: bool,
    collector: _IssueCollector,
) -> None:
    if any(pat.search(line) for pat in _SQL_INJECTION_PATTERNS):
        collector.add({
            "category": "SQL_INJECTION",
            "severity": "CRITICAL",
            "file": rel_path,
            "line": line_no,
            "message": "String-interpolated SQL statement detected (potential SQL Injection).",
            "recommendation": "Use parameterized SQL queries (`cursor.execute('SELECT ... WHERE id = ?', (val,))`).",
        })
    if any(pat.search(line) for pat in _XSS_PATTERNS):
        if "escapeHtml" not in line and "DOMPurify" not in line and "sanitize" not in line.lower():
            collector.add({
                "category": "XSS",
                "severity": "HIGH",
                "file": rel_path,
                "line": line_no,
                "message": "Potentially unsanitized HTML sink (`innerHTML` / `outerHTML` / `document.write`) detected.",
                "recommendation": "Use `textContent` for text data or sanitize HTML string via an escaping helper before assignment.",
            })
    if not has_resolve and any(pat.search(line) for pat in _PATH_TRAVERSAL_PATTERNS):
        collector.add({
            "category": "PATH_TRAVERSAL",
            "severity": "HIGH",
            "file": rel_path,
            "line": line_no,
            "message": "Relative parent traversal pattern (`..`) without canonical path resolution check.",
            "recommendation": "Canonicalize paths with `Path.resolve()` and enforce workspace root containment.",
        })
    for secret_label, pat in _SECRET_PATTERNS:
        if pat.search(line):
            collector.add({
                "category": "HARDCODED_SECRET",
                "severity": "CRITICAL",
                "file": rel_path,
                "line": line_no,
                "message": f"{secret_label} found hardcoded in source.",
                "recommendation": "Load secrets from environment variables (`os.environ.get(...)`) or a git-ignored `.env` vault.",
            })
            break
    if any(pat.search(line) for pat in _UNSAFE_EXEC_PATTERNS):
        collector.add({
            "category": "UNSAFE_EVAL_EXEC",
            "severity": "CRITICAL",
            "file": rel_path,
            "line": line_no,
            "message": "Unsafe dynamic code or shell execution detected.",
            "recommendation": "Avoid `eval`/`exec` and `shell=True`; pass argument lists directly to `subprocess.run([...], shell=False)`.",
        })


def _scan_file_security(file_path: Path, ws_dir: Path, collector: _IssueCollector) -> None:
    rel_path = file_path.relative_to(ws_dir).as_posix()
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    has_resolve = ".resolve(" in source or "realpath(" in source
    for idx, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
            continue
        _scan_line_patterns(line, rel_path, idx, has_resolve, collector)
    if file_path.suffix.lower() == ".py":
        for ast_issue in _scan_python_ast_security(source, rel_path):
            collector.add(ast_issue)


def scan_code_security(ws_dir: Path) -> dict[str, Any]:
    ws_dir = Path(ws_dir).resolve()
    if not ws_dir.exists():
        return {
            "workspace": str(ws_dir),
            "ok": True,
            "total_issues": 0,
            "severity_counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0},
            "issues": [],
        }
    collector = _IssueCollector()
    for file_path in sorted(ws_dir.rglob("*")):
        if any(part in IGNORED_DIRS for part in file_path.parts):
            continue
        if not file_path.is_file() or file_path.suffix.lower() not in SCANNABLE_EXTENSIONS:
            continue
        _scan_file_security(file_path, ws_dir, collector)

    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0}
    for item in collector.issues:
        sev = item.get("severity", "MEDIUM")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    return {
        "workspace": str(ws_dir),
        "ok": severity_counts["CRITICAL"] == 0 and severity_counts["HIGH"] == 0,
        "total_issues": len(collector.issues),
        "severity_counts": severity_counts,
        "issues": collector.issues,
    }


def _collect_smoke_targets(ws_dir: Path) -> tuple[list[Path], list[Path]]:
    py_files: list[Path] = []
    json_files: list[Path] = []
    for file_path in sorted(ws_dir.rglob("*")):
        if any(part in IGNORED_DIRS for part in file_path.parts) or not file_path.is_file():
            continue
        suffix = file_path.suffix.lower()
        if suffix == ".py":
            py_files.append(file_path)
        elif suffix == ".json":
            json_files.append(file_path)
    return py_files, json_files


def _check_python_smoke(py_path: Path, ws_dir: Path) -> list[dict[str, Any]]:
    rel_path = py_path.relative_to(ws_dir).as_posix()
    try:
        source = py_path.read_text(encoding="utf-8", errors="replace")
        ast.parse(source, filename=rel_path)
    except SyntaxError as exc:
        return [{"type": "python_syntax_error", "file": rel_path, "line": exc.lineno or 1, "message": f"SyntaxError: {exc.msg}"}]
    try:
        proc = run_process([sys.executable, "-m", "py_compile", str(py_path)], cwd=ws_dir, timeout_s=15.0)
        if proc.returncode != 0:
            err_msg = (proc.stderr or proc.stdout or "py_compile failed").strip()
            return [{"type": "py_compile_error", "file": rel_path, "line": 1, "message": err_msg}]
    except (OSError, ValueError) as exc:
        return [{"type": "py_compile_exception", "file": rel_path, "line": 1, "message": str(exc)}]
    return []


def _check_json_smoke(json_path: Path, ws_dir: Path) -> list[dict[str, Any]]:
    rel_path = json_path.relative_to(ws_dir).as_posix()
    try:
        json.loads(json_path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        return [{"type": "json_decode_error", "file": rel_path, "line": exc.lineno, "message": f"Invalid JSON: {exc.msg}"}]
    return []


def run_workspace_smoke_check(ws_dir: Path) -> dict[str, Any]:
    ws_dir = Path(ws_dir).resolve()
    if not ws_dir.exists():
        return {
            "ok": False,
            "errors": [{"type": "missing_workspace", "file": str(ws_dir), "message": "Workspace directory does not exist."}],
            "security": scan_code_security(ws_dir),
        }

    py_files, json_files = _collect_smoke_targets(ws_dir)
    errors: list[dict[str, Any]] = []
    for py_path in py_files:
        errors.extend(_check_python_smoke(py_path, ws_dir))
    for json_path in json_files:
        errors.extend(_check_json_smoke(json_path, ws_dir))

    graph = build_workspace_code_graph(ws_dir)
    for broken in graph.get("broken_references", []):
        errors.append({
            "type": broken.get("type", "broken_reference"),
            "file": broken.get("source", ""),
            "line": broken.get("line", 1),
            "target": broken.get("target", ""),
            "message": f"Broken reference `{broken.get('target', '')}` in `{broken.get('source', '')}`.",
        })

    return {"ok": len(errors) == 0, "errors": errors, "security": scan_code_security(ws_dir)}
