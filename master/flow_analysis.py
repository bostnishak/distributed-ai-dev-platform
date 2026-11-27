"""Follow values between the functions of a Python project.

Three questions a single-line scanner cannot answer: does a value a request sends reach a dangerous call through
other functions; is the result of a function that may return None used without a check; and which functions are never
referred to anywhere.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

_SKIP = {".history", ".ai-os", "venv", ".venv", "__pycache__", "node_modules", "build", "dist"}
_ROUTE_VERBS = {"get", "post", "put", "patch", "delete", "route", "websocket", "api_route"}
_ALWAYS_SINKS = {"os.system", "os.popen", "eval", "exec"}


@dataclass
class Function:
    path: str
    node: ast.FunctionDef | ast.AsyncFunctionDef

    @property
    def name(self) -> str:
        return self.node.name

    def params(self) -> list[str]:
        args = self.node.args
        return [a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs) if a.arg not in ("self", "cls")]

    def is_route(self) -> bool:
        return any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in _ROUTE_VERBS for d in self.node.decorator_list)


def _trees(ws_dir: Path) -> dict[str, ast.Module]:
    trees = {}
    for path in sorted(ws_dir.rglob("*.py")):
        relative = path.relative_to(ws_dir)
        if _SKIP & set(relative.parts):
            continue
        try:
            trees[relative.as_posix()] = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
    return trees


def _functions(trees: dict[str, ast.Module]) -> list[Function]:
    return [Function(path, node) for path, tree in trees.items() for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)]


def _called(call: ast.Call) -> str:
    try:
        return ast.unparse(call.func)
    except (ValueError, RecursionError):
        return ""


def _uses(node: ast.AST, names: set[str]) -> bool:
    return any(isinstance(n, ast.Name) and n.id in names for n in ast.walk(node))


def _tainted_names(function: Function, seeds: set[str]) -> set[str]:
    """The seeds plus every local computed from them. int()/float() of a value is no longer attacker text."""
    tainted = set(seeds)
    assignments = [n for n in ast.walk(function.node) if isinstance(n, ast.Assign)]
    for _round in range(3):
        for node in assignments:
            if isinstance(node.value, ast.Call) and _called(node.value) in ("int", "float", "bool", "len", "shlex.quote"):
                continue
            if _uses(node.value, tainted):
                tainted |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    return tainted


_SQL_RE = re.compile(r"\b(?:select|insert|update|delete|create|drop|alter|with)\b", re.IGNORECASE)


def _built_sql(node: ast.AST, function: Function) -> bool:
    """An f-string or concatenation holding SQL words, directly or through a local variable."""
    if isinstance(node, ast.Name):
        values = [a.value for a in ast.walk(function.node) if isinstance(a, ast.Assign) and any(isinstance(t, ast.Name) and t.id == node.id for t in a.targets)]
        return any(isinstance(v, ast.JoinedStr | ast.BinOp) and _built_sql(v, function) for v in values)
    if not isinstance(node, ast.JoinedStr | ast.BinOp):
        return False
    return any(isinstance(c, ast.Constant) and isinstance(c.value, str) and _SQL_RE.search(c.value) for c in ast.walk(node))


def _sink(call: ast.Call, tainted: set[str], function: Function) -> str:
    """The name of the dangerous operation when a tainted value reaches it in an unsafe position."""
    name = _called(call)
    first = call.args[0] if call.args else None
    if first is None or not _uses(first, tainted):
        return ""
    if name in _ALWAYS_SINKS:
        return name
    if name.startswith("subprocess.") and any(k.arg == "shell" and getattr(k.value, "value", False) is True for k in call.keywords):
        return f"{name}(shell=True)"
    if name.endswith((".execute", ".executescript", ".executemany")) and _built_sql(first, function):
        return f"{name} (SQL metni)"
    if name == "open":
        return "open (dosya yolu)"
    return ""


def _passed_on(call: ast.Call, callee: Function, tainted: set[str]) -> set[str]:
    params = callee.params()
    reached = {params[i] for i, arg in enumerate(call.args) if i < len(params) and _uses(arg, tainted)}
    return reached | {k.arg for k in call.keywords if k.arg in params and _uses(k.value, tainted)}


def _follow(function: Function, seeds: set[str], table: dict[str, Function], trail: tuple[str, ...]) -> Iterator[str]:
    tainted = _tainted_names(function, seeds)
    for call in (n for n in ast.walk(function.node) if isinstance(n, ast.Call)):
        if sink := _sink(call, tainted, function):
            yield f"{function.path}:{call.lineno} istekten gelen veri {sink} içine ulaşıyor: {' -> '.join(trail)}"
        callee = table.get(_called(call).rsplit(".", 1)[-1])
        if callee and callee.name not in trail and len(trail) < 5 and (reached := _passed_on(call, callee, tainted)):
            yield from _follow(callee, reached, table, (*trail, callee.name))


def tainted_flows(ws_dir: Path) -> list[str]:
    """Request values that reach a command, SQL text or file path, possibly through several functions."""
    functions = _functions(_trees(ws_dir))
    table = {f.name: f for f in functions}
    found = [line for f in functions if f.is_route() and f.params() for line in _follow(f, set(f.params()), table, (f.name,))]
    return list(dict.fromkeys(found))[:10]


def _may_return_none(function: Function) -> bool:
    returns = [n for n in ast.walk(function.node) if isinstance(n, ast.Return)]
    valued = [r for r in returns if r.value is not None and not (isinstance(r.value, ast.Constant) and r.value.value is None)]
    empty = len(returns) > len(valued)
    annotation = ast.unparse(function.node.returns) if function.node.returns else ""
    return bool(valued) and (empty or "None" in annotation or "Optional" in annotation)


def _guarded(function: Function, name: str) -> bool:
    for node in ast.walk(function.node):
        tests = [node.test] if isinstance(node, ast.If | ast.While | ast.IfExp | ast.Assert) else (node.values if isinstance(node, ast.BoolOp) else [])
        if any(_uses(test, {name}) for test in tests):
            return True
        if isinstance(node, ast.Try):
            return True
    return False


def none_accesses(ws_dir: Path) -> list[str]:
    """`x = find(...)` followed by `x.field` or `x[...]` although find may return None and x is never checked."""
    functions = _functions(_trees(ws_dir))
    nullable = {f.name for f in functions if _may_return_none(f)}
    found = []
    for function in functions:
        results = {t.id for n in ast.walk(function.node) if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call | ast.Await)
                   for call in [n.value.value if isinstance(n.value, ast.Await) else n.value] if isinstance(call, ast.Call) and _called(call).rsplit(".", 1)[-1] in nullable
                   for t in n.targets if isinstance(t, ast.Name)}
        for node in ast.walk(function.node):
            if isinstance(node, ast.Attribute | ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id in results and not _guarded(function, node.value.id):
                found.append(f"{function.path}:{node.lineno} {node.value.id} None olabilir ama denetlenmeden kullanılıyor")
    return list(dict.fromkeys(found))[:10]


def dead_functions(ws_dir: Path) -> list[str]:
    """Functions nothing refers to: not called, not passed on, not decorated, not an entry point or a test."""
    trees = _trees(ws_dir)
    used: set[str] = set()
    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.isidentifier():
                used.add(node.value)
            elif isinstance(node, ast.ImportFrom):
                used.update(alias.name for alias in node.names)
    return [f"{f.path}:{f.node.lineno} {f.name} hiçbir yerden kullanılmıyor" for f in _functions(trees)
            if f.name not in used and not f.node.decorator_list and f.name != "main" and not f.name.startswith(("test_", "__", "visit_", "do_", "on_"))][:10]


def report(ws_dir: Path) -> str:
    """One chat line with what was found, or ''."""
    found = [*tainted_flows(ws_dir), *none_accesses(ws_dir), *dead_functions(ws_dir)]
    return f"Veri akışı denetimi {len(found)} bulgu: " + "; ".join(found[:4]) if found else ""
