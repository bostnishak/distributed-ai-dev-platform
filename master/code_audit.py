"""Model-free analysis of a generated project: compiler diagnostics, input-to-sink data flow, query performance and licences.

Every finding names a file and line. Nothing here runs the project's code.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import static_lint
from process_utils import run_process

_SKIP = {".history", "venv", ".venv", "node_modules", "__pycache__", ".git"}
_SOURCES = ("input", "request.args", "request.form", "request.json", "request.values", "request.get_json", "sys.argv", "request.query_params", "request.path_params")
_SINKS = {"execute": "SQL", "executescript": "SQL", "executemany": "SQL", "system": "kabuk", "popen": "kabuk", "eval": "kod", "exec": "kod", "render_template_string": "HTML şablonu"}
_ROUTE_RE = re.compile(r"\.(?:get|post|put|delete|patch|route)$")
_SQL_RE = re.compile(r"""["']\s*(SELECT\s[^"']+?\sWHERE\s[^"']+)["']""", re.IGNORECASE)
_COPYLEFT = re.compile(r"\b(?:A?GPL|GNU (?:Affero )?General Public)\b", re.IGNORECASE)
_PERMISSIVE = re.compile(r"\b(?:MIT|Apache|BSD)\b")


def _files(ws_dir: Path, suffix: str) -> Iterator[Path]:
    for path in sorted(ws_dir.rglob(f"*{suffix}")):
        if path.is_file() and not _SKIP & set(path.relative_to(ws_dir).parts):
            yield path


def diagnostics(ws_dir: Path) -> list[str]:
    """Errors a compiler would report: undefined names and syntax errors (Python), parse errors (JavaScript)."""
    found: list[str] = []
    if any(_files(ws_dir, ".py")):
        try:
            res = run_process([sys.executable, "-m", "ruff", "check", "--isolated", "--no-cache", "--select", "E9,F63,F7,F82,F811", "--output-format", "concise", str(ws_dir)], timeout_s=60)
            found += [line.replace(str(ws_dir) + "\\", "").replace(str(ws_dir) + "/", "") for line in res.stdout.splitlines() if re.search(r":\d+:\d+:", line)]
        except (OSError, subprocess.SubprocessError):
            found.append("ruff çalıştırılamadı; Python tanılaması atlandı")
    node = shutil.which("node")
    for path in _files(ws_dir, ".js") if node else []:
        try:
            res = run_process([node, "--check", str(path)], timeout_s=20)
        except (OSError, subprocess.SubprocessError):
            continue
        if res.returncode and "import statement outside a module" not in res.stderr:
            line = next((x for x in res.stderr.splitlines() if "Error" in x), "sözdizimi hatası")
            found.append(f"{path.relative_to(ws_dir).as_posix()}: {line}")
    return found + static_lint.findings(ws_dir)


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}"
    return node.id if isinstance(node, ast.Name) else _dotted(node.func) if isinstance(node, ast.Call) else ""


def _names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _tainted(node: ast.AST, tainted: set[str]) -> bool:
    if isinstance(node, ast.Call) and _dotted(node.func) in ("int", "float", "bool", "len", "shlex.quote", "html.escape", "escape"):
        return False  # converted or escaped: the dangerous characters are gone
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id in tainted:
            return True
        if isinstance(child, ast.Call | ast.Attribute | ast.Subscript) and _dotted(child.value if isinstance(child, ast.Subscript) else child).startswith(_SOURCES):
            return True
    return False


def _route_params(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    routed = any(isinstance(d, ast.Call) and _ROUTE_RE.search(_dotted(d.func)) for d in func.decorator_list)
    plain = ("int", "float", "bool")
    return {a.arg for a in func.args.args if routed and not (isinstance(a.annotation, ast.Name) and a.annotation.id in plain)}


def flows(source: str) -> list[tuple[int, str]]:
    """(line, sink kind) where user input reaches a dangerous call as part of the command text itself."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found: list[tuple[int, str]] = []
    scopes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)] or [tree]
    for scope in scopes:
        tainted = _route_params(scope) if not isinstance(scope, ast.Module) else set()
        ordered = sorted((n for n in ast.walk(scope) if isinstance(n, ast.Assign | ast.AugAssign | ast.Call)), key=lambda n: (n.lineno, n.col_offset))
        for node in ordered:
            if isinstance(node, ast.Assign | ast.AugAssign):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = set().union(*(_names(t) for t in targets))
                tainted = tainted | names if _tainted(node.value, tainted) else tainted - names if isinstance(node, ast.Assign) else tainted
                continue
            kind = _SINKS.get(_dotted(node.func).rsplit(".", 1)[-1])
            if kind and node.args and _tainted(node.args[0], tainted):  # args[0] only: bound query parameters are safe
                found.append((node.lineno, kind))
    return found


def loops_with_queries(source: str) -> list[int]:
    """Lines of database calls inside a loop (one query per row: N+1)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    lines = {call.lineno for loop in ast.walk(tree) if isinstance(loop, ast.For | ast.AsyncFor | ast.While)
             for stmt in loop.body for call in ast.walk(stmt)
             if isinstance(call, ast.Call) and _dotted(call.func).rsplit(".", 1)[-1] in ("execute", "query") and re.search(r"cur|conn|db|session", _dotted(call.func), re.IGNORECASE)}
    return sorted(lines)


def _schema_db(ws_dir: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for suffix in (".sql", ".py") for p in _files(ws_dir, suffix))
    for statement in re.findall(r"CREATE\s+(?:TABLE|(?:UNIQUE\s+)?INDEX)\s[^;\"']*(?:\([^;]*?\))", text, re.IGNORECASE | re.DOTALL):
        try:
            conn.execute(statement)
        except sqlite3.Error:
            continue
    return conn


def full_scans(ws_dir: Path) -> list[str]:
    """Filtered SELECTs that SQLite would answer by reading the whole table (a missing index)."""
    conn = _schema_db(ws_dir)
    found: list[str] = []
    try:
        for path in _files(ws_dir, ".py"):
            for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                for query in _SQL_RE.findall(line):
                    try:
                        plan = conn.execute("EXPLAIN QUERY PLAN " + query, [None] * query.count("?")).fetchall()
                    except sqlite3.Error:
                        continue
                    if any(str(row[-1]).startswith("SCAN ") for row in plan):
                        found.append(f"{path.relative_to(ws_dir).as_posix()}:{number} sorgu tüm tabloyu tarıyor (indeks yok)")
    finally:
        conn.close()
    return found


def _project_licence(ws_dir: Path, request: str) -> str:
    licence = ws_dir / "LICENSE"
    text = (licence.read_text(encoding="utf-8", errors="replace")[:400] if licence.is_file() else "") + "\n" + request
    manifest = ws_dir / "package.json"
    if manifest.is_file():
        try:
            text += " " + str(json.loads(manifest.read_text(encoding="utf-8")).get("license", ""))
        except (ValueError, OSError):
            pass
    match = _PERMISSIVE.search(text)
    return match.group(0) if match else ""


def licence_conflicts(ws_dir: Path, request: str, licence_of: Callable[[str, str], str]) -> list[str]:
    """Copyleft dependencies in a project that says it is MIT, Apache or BSD."""
    import package_check

    mine = _project_licence(ws_dir, request)
    if not mine:
        return []
    return [f"'{name}' lisansı {licence} — proje {mine} olarak istenmiş; uyumsuz olabilir"
            for registry, name in package_check.declared(ws_dir) if (licence := licence_of(registry, name)) and _COPYLEFT.search(licence)]


def registry_licence(registry: str, name: str) -> str:
    import package_check

    try:
        data = package_check.registry_lookup(registry, name) or {}
    except (OSError, ValueError):
        return ""
    info = data.get("info", data)
    classifiers = " ".join(c for c in info.get("classifiers", []) if c.startswith("License"))
    return str(info.get("license_expression") or info.get("license") or "")[:80] + " " + classifiers


def report(ws_dir: Path, request: str = "") -> list[str]:
    """Chat warning lines, most serious first."""
    lines: list[str] = []
    if errors := diagnostics(ws_dir):
        lines.append("Statik tanılama: " + "; ".join(errors[:3]))
    risky = [f"{p.relative_to(ws_dir).as_posix()}:{line} kullanıcı girdisi {kind} komutuna ekleniyor"
             for p in _files(ws_dir, ".py") for line, kind in flows(p.read_text(encoding="utf-8", errors="replace"))]
    if risky:
        lines.append("Veri akışı: " + "; ".join(risky[:3]))
    slow = [f"{p.relative_to(ws_dir).as_posix()}:{line} döngü içinde sorgu (N+1)" for p in _files(ws_dir, ".py")
            for line in loops_with_queries(p.read_text(encoding="utf-8", errors="replace"))] + full_scans(ws_dir)
    if slow:
        lines.append("Performans: " + "; ".join(slow[:3]))
    if conflicts := licence_conflicts(ws_dir, request, registry_licence):
        lines.append("Lisans: " + "; ".join(conflicts[:3]))
    return lines
