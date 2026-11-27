"""Testing the tests: plant small bugs in a generated project and see whether its own tests notice.

Mutants are made from the syntax tree (one change each) and run in the same offline Docker sandbox as the project.
"""

from __future__ import annotations

import ast
import shutil
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import workspace_docker

_SWAPS: dict[type, type] = {
    ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
    ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv, ast.And: ast.Or, ast.Or: ast.And, ast.In: ast.NotIn, ast.NotIn: ast.In,
}
_MAX_MUTANTS = 12


@dataclass(frozen=True)
class Mutant:
    path: str
    line: int
    change: str
    source: str


def _sites(tree: ast.AST) -> Iterator[tuple[int, str, Callable[[], None]]]:
    """(line, description, apply) for every place one small bug can be planted."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and type(node.ops[0]) in _SWAPS:
            new = _SWAPS[type(node.ops[0])]
            yield node.lineno, f"{type(node.ops[0]).__name__}->{new.__name__}", lambda n=node, c=new: n.ops.__setitem__(0, c())
        elif isinstance(node, ast.BinOp | ast.BoolOp) and type(node.op) in _SWAPS:
            new = _SWAPS[type(node.op)]
            yield node.lineno, f"{type(node.op).__name__}->{new.__name__}", lambda n=node, c=new: setattr(n, "op", c())
        elif isinstance(node, ast.If) and not isinstance(node.test, ast.Compare):
            yield node.lineno, "koşul tersine", lambda n=node: setattr(n, "test", ast.UnaryOp(op=ast.Not(), operand=n.test))
        elif isinstance(node, ast.Return) and node.value is not None and not (isinstance(node.value, ast.Constant) and node.value.value is None):
            yield node.lineno, "dönüş None", lambda n=node: setattr(n, "value", ast.Constant(value=None))
        elif isinstance(node, ast.Constant) and type(node.value) is int:
            yield node.lineno, f"{node.value}->{node.value + 1}", lambda n=node: setattr(n, "value", n.value + 1)


def mutants(source: str, path: str, limit: int = _MAX_MUTANTS) -> list[Mutant]:
    """Up to `limit` single-change variants, spread over the file."""
    try:
        total = len(list(_sites(ast.parse(source))))
    except SyntaxError:
        return []
    step = max(total // limit, 1)
    out: list[Mutant] = []
    for index in range(0, total, step):
        tree = ast.parse(source)
        line, change, apply = list(_sites(tree))[index]
        apply()
        ast.fix_missing_locations(tree)
        out.append(Mutant(path, line, change, ast.unparse(tree)))
    return out[:limit]


def _targets(ws_dir: Path) -> list[Path]:
    skip = {"tests", ".history", "venv", ".venv", "__pycache__"}
    return [p for p in sorted(ws_dir.rglob("*.py")) if not skip & set(p.relative_to(ws_dir).parts) and not p.name.startswith("test_")]


def run(ws_dir: Path, runs_ok: Callable[[Path], bool], limit: int = _MAX_MUTANTS) -> tuple[int, list[Mutant]]:
    """(mutants tried, mutants the tests did not notice). The project folder is never modified."""
    files = _targets(ws_dir)
    if not files:
        return 0, []
    share = max(limit // len(files), 2)
    planned = [m for f in files for m in mutants(f.read_text(encoding="utf-8", errors="replace"), f.relative_to(ws_dir).as_posix(), share)][:limit]
    survivors: list[Mutant] = []
    with tempfile.TemporaryDirectory(prefix="cm6453_mut_") as tmp:
        stage = Path(tmp) / "ws"
        shutil.copytree(ws_dir, stage, ignore=shutil.ignore_patterns(".history", "__pycache__", ".git", "venv"))
        if not runs_ok(stage):
            return 0, []  # tests already fail: mutation results would mean nothing
        for mutant in planned:
            target = stage / mutant.path
            original = target.read_text(encoding="utf-8", errors="replace")
            target.write_text(mutant.source, encoding="utf-8")
            if runs_ok(stage):
                survivors.append(mutant)
            target.write_text(original, encoding="utf-8")
    return len(planned), survivors


def report(ws_dir: Path, pkgs: list[str]) -> str:
    """One chat line with the kill rate, or '' when there are no tests or no sandbox."""
    tests = ws_dir / "tests"
    if not tests.is_dir() or not any(tests.glob("test_*.py")) or not workspace_docker.available():
        return ""
    tried, survived = run(ws_dir, lambda stage: not workspace_docker.run_tests(stage, pkgs))
    if not tried:
        return ""
    rate = round(100 * (tried - len(survived)) / tried)
    line = f"Mutasyon testi: yerleştirilen {tried} hatanın {tried - len(survived)} tanesini testler yakaladı (%{rate})."
    if rate < 80:
        line += " Testler zayıf; yakalanmayanlar: " + ", ".join(f"{m.path}:{m.line} ({m.change})" for m in survived[:3])
    return line
