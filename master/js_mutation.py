"""Mutation testing for JavaScript: plant one small bug at a time and see whether the project's own tests notice.

Sites are found with Tree-sitter. The tests run on a copy of the project with Node's permission model (it may read
only that copy: no writing, no network, no child processes) inside a Windows job with memory and process limits.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

import isolation
import ts_symbols
from mutation import Mutant

_SWAPS = {"<": "<=", "<=": "<", ">": ">=", ">=": ">", "===": "!==", "!==": "===", "==": "!=", "!=": "==", "+": "-", "-": "+", "*": "/", "&&": "||", "||": "&&"}
_SKIP = {".history", ".ai-os", "node_modules", "dist", "vendor", "venv"}


def is_test(path: Path) -> bool:
    return path.name.endswith((".test.js", ".test.mjs", ".spec.js")) or "tests" in path.parts or "test" in path.parts


def _files(ws_dir: Path, tests: bool) -> list[Path]:
    found = [p for p in sorted(ws_dir.rglob("*")) if p.suffix in (".js", ".mjs") and p.is_file() and not _SKIP & set(p.relative_to(ws_dir).parts)]
    return [p for p in found if is_test(p.relative_to(ws_dir)) == tests]


def _sites(data: bytes, root) -> list[tuple[int, int, bytes, str, int]]:
    """(start byte, end byte, replacement, description, line) of every place one small bug can be planted."""
    sites = []
    stack = [root]
    while stack:
        node = stack.pop()
        stack.extend(reversed(node.children))
        line = node.start_point[0] + 1
        if node.type == "binary_expression":
            operator = node.child_by_field_name("operator")
            if operator is not None and operator.type in _SWAPS:
                sites.append((operator.start_byte, operator.end_byte, _SWAPS[operator.type].encode(), f"{operator.type} -> {_SWAPS[operator.type]}", line))
        elif node.type == "number" and data[node.start_byte : node.end_byte].isdigit():
            value = int(data[node.start_byte : node.end_byte])
            sites.append((node.start_byte, node.end_byte, str(value + 1).encode(), f"{value} -> {value + 1}", line))
        elif node.type == "return_statement" and node.named_child_count:
            value = node.named_children[0]
            sites.append((value.start_byte, value.end_byte, b"undefined", "dönüş undefined", line))
        elif node.type == "if_statement":
            condition = node.child_by_field_name("condition")
            if condition is not None and condition.named_child_count and condition.named_children[0].type != "binary_expression":
                inner = condition.named_children[0]
                sites.append((inner.start_byte, inner.end_byte, b"!(" + data[inner.start_byte : inner.end_byte] + b")", "koşul tersine", line))
    return sites


def mutants(source: str, path: str, limit: int = 12) -> list[Mutant]:
    parser = ts_symbols._parser(".js")
    if parser is None:
        return []
    data = source.encode("utf-8")
    root = parser.parse(data).root_node
    if root.has_error:
        return []
    sites = _sites(data, root)
    step = max(len(sites) // limit, 1)
    return [Mutant(path, line, change, (data[:start] + new + data[end:]).decode("utf-8")) for start, end, new, change, line in sites[::step]][:limit]


def run_tests(ws_dir: Path) -> str:
    """"" when every test file passes, else the end of the failing output. OSError when it cannot be run safely."""
    node = shutil.which("node")
    if not node:
        raise OSError("node bulunamadı")
    for test in _files(ws_dir, tests=True):
        done = isolation.run_capped([node, "--permission", f"--allow-fs-read={ws_dir.resolve()}\\*", str(test.resolve())], memory_mb=1024, processes=4, timeout_s=30.0)
        if done.returncode != 0:
            return (done.stdout + done.stderr)[-1200:] or f"{test.name}: çıkış kodu {done.returncode}"
    return ""


def has_tests(ws_dir: Path) -> bool:
    return bool(_files(ws_dir, tests=True))


def run(ws_dir: Path, runs_ok: Callable[[Path], bool] | None = None, limit: int = 12) -> tuple[int, list[Mutant]]:
    """(mutants tried, mutants the tests did not notice). The project folder is never modified."""
    runs_ok = runs_ok or (lambda stage: not run_tests(stage))
    sources = _files(ws_dir, tests=False)
    if not sources or not has_tests(ws_dir):
        return 0, []
    share = max(limit // len(sources), 2)
    planned = [m for f in sources for m in mutants(f.read_text(encoding="utf-8", errors="replace"), f.relative_to(ws_dir).as_posix(), share)][:limit]
    survivors: list[Mutant] = []
    with tempfile.TemporaryDirectory(prefix="cm6453_jsmut_", ignore_cleanup_errors=True) as tmp:
        stage = Path(tmp).resolve() / "ws"
        shutil.copytree(ws_dir, stage, ignore=shutil.ignore_patterns(".history", ".git", ".ai-os"))
        if not runs_ok(stage):
            return 0, []  # tests already fail: mutation results would mean nothing
        for mutant in planned:
            target = stage / mutant.path
            original = target.read_bytes()
            target.write_text(mutant.source, encoding="utf-8")
            if runs_ok(stage):
                survivors.append(mutant)
            target.write_bytes(original)
    return len(planned), survivors


def report(ws_dir: Path) -> str:
    """One chat line with the kill rate, or '' when there are no JavaScript tests or they cannot run."""
    try:
        tried, survived = run(ws_dir)
    except OSError:
        return ""
    if not tried:
        return ""
    rate = round(100 * (tried - len(survived)) / tried)
    line = f"JavaScript mutasyon testi: yerleştirilen {tried} hatanın {tried - len(survived)} tanesini testler yakaladı (%{rate})."
    if rate < 80:
        line += " Testler zayıf; yakalanmayanlar: " + ", ".join(f"{m.path}:{m.line} ({m.change})" for m in survived[:3])
    return line
