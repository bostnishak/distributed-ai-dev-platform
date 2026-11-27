"""Prove or refute "this value never goes negative" for small methods with Z3, without running them or asking a model.

The method is executed symbolically: parameters and the attribute are unknown integers, guards that raise cut paths
off, and Z3 is asked for any input that leaves the attribute negative although it started non-negative. Anything outside
the supported subset (loops, calls, other types) is reported as not provable, never as proved.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

_SKIP = {".history", "venv", ".venv", "tests", "__pycache__"}


class Unsupported(Exception):
    pass


@dataclass(frozen=True)
class Verdict:
    method: str
    proved: bool
    counterexample: str = ""


def _expr(node: ast.AST, env: dict):
    import z3

    if isinstance(node, ast.Constant) and type(node.value) in (int, bool):
        return z3.IntVal(node.value) if type(node.value) is int else z3.BoolVal(node.value)
    if isinstance(node, ast.Name) and node.id in env:
        return env[node.id]
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self" and f"self.{node.attr}" in env:
        return env[f"self.{node.attr}"]
    if isinstance(node, ast.UnaryOp):
        value = _expr(node.operand, env)
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.Not):
            return z3.Not(value)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add | ast.Sub | ast.Mult):
        left, right = _expr(node.left, env), _expr(node.right, env)
        return left + right if isinstance(node.op, ast.Add) else left - right if isinstance(node.op, ast.Sub) else left * right
    if isinstance(node, ast.BoolOp):
        parts = [_expr(v, env) for v in node.values]
        return z3.And(*parts) if isinstance(node.op, ast.And) else z3.Or(*parts)
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        left, right = _expr(node.left, env), _expr(node.comparators[0], env)
        table = {ast.Lt: left < right, ast.LtE: left <= right, ast.Gt: left > right, ast.GtE: left >= right, ast.Eq: left == right, ast.NotEq: left != right}
        return table[type(node.ops[0])]
    raise Unsupported(ast.dump(node)[:60])


def _target(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
        return f"self.{node.attr}"
    raise Unsupported("atama hedefi")


def _run(statements: list[ast.stmt], env: dict, condition) -> list[tuple[object, dict]]:
    """Every normally finishing path as (path condition, final values); raising paths are dropped."""
    import z3

    for index, node in enumerate(statements):
        rest = statements[index + 1 :]
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            env = {**env, _target(node.targets[0]): _expr(node.value, env)}
        elif isinstance(node, ast.AugAssign):
            name = _target(node.target)
            env = {**env, name: _expr(ast.BinOp(left=node.target, op=node.op, right=node.value), env)}
        elif isinstance(node, ast.If):
            test = _expr(node.test, env)
            return _run([*node.body, *rest], env, z3.And(condition, test)) + _run([*node.orelse, *rest], env, z3.And(condition, z3.Not(test)))
        elif isinstance(node, ast.Raise):
            return []
        elif isinstance(node, ast.Return):
            return [(condition, env)]
        elif not isinstance(node, ast.Pass | ast.Expr) or (isinstance(node, ast.Expr) and not isinstance(node.value, ast.Constant)):
            raise Unsupported(type(node).__name__)
    return [(condition, env)]


def check_method(func: ast.FunctionDef, attribute: str) -> Verdict:
    import z3

    params = {a.arg: z3.Int(a.arg) for a in func.args.args if a.arg != "self"}
    before = z3.Int(attribute)
    paths = _run(func.body, {**params, f"self.{attribute}": before}, z3.BoolVal(True))
    solver = z3.Solver()
    solver.set("timeout", 4000)
    solver.add(before >= 0, z3.Or(*[z3.And(condition, env[f"self.{attribute}"] < 0) for condition, env in paths]) if paths else z3.BoolVal(False))
    answer = solver.check()
    if answer == z3.unsat:
        return Verdict(func.name, True)
    if answer != z3.sat:
        raise Unsupported("çözücü zaman aşımı")
    model = solver.model()
    values = [f"{attribute}={model.eval(before, model_completion=True)}", *[f"{n}={model.eval(v, model_completion=True)}" for n, v in params.items()]]
    return Verdict(func.name, False, ", ".join(values))


def analyse(source: str) -> list[tuple[str, str, Verdict | None]]:
    """(class, attribute, verdict or None when unprovable) for every method that changes a numeric attribute."""
    out = []
    for cls in (n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.ClassDef)):
        methods = [m for m in cls.body if isinstance(m, ast.FunctionDef)]
        init = next((m for m in methods if m.name == "__init__"), None)
        numeric = [t.attr for node in (ast.walk(init) if init else []) if isinstance(node, ast.Assign) for t in node.targets
                   if isinstance(t, ast.Attribute) and isinstance(node.value, ast.Constant) and type(node.value.value) is int]
        for attribute in numeric:
            for method in (m for m in methods if m.name != "__init__"):
                written = any(isinstance(t, ast.Attribute) and t.attr == attribute
                              for node in ast.walk(method) if isinstance(node, ast.Assign | ast.AugAssign)
                              for t in (node.targets if isinstance(node, ast.Assign) else [node.target]))
                if not written:
                    continue
                try:
                    out.append((cls.name, attribute, check_method(method, attribute)))
                except (Unsupported, KeyError):
                    out.append((cls.name, attribute, None))
    return out


def report(ws_dir: Path, rule: str) -> str:
    """A chat line when the rule is a non-negativity rule Z3 can decide; '' when it is not that kind of rule."""
    if not any(word in rule.casefold() for word in ("negatif", "negative", "sıfırın altına", "eksiye")):
        return ""
    results = []
    for path in sorted(ws_dir.rglob("*.py")):
        if _SKIP & set(path.relative_to(ws_dir).parts):
            continue
        try:
            results += [(path.name, *item) for item in analyse(path.read_text(encoding="utf-8", errors="replace"))]
        except SyntaxError:
            continue
    if not results or all(verdict is None for *_x, verdict in results):
        return ""
    broken = [f"{cls}.{v.method}: {v.counterexample}" for _f, cls, _a, v in results if v and not v.proved]
    unknown = [f"{cls}.{attr}" for _f, cls, attr, v in results if v is None]
    if broken:
        return f"İş kuralı İHLAL EDİLİYOR (Z3 karşı örneği): \"{rule}\" — " + "; ".join(broken[:3])
    proved = sorted({f"{cls}.{v.method}" for _f, cls, _a, v in results if v})
    tail = f" İspatlanamayan (desteklenmeyen kod): {', '.join(unknown[:3])}." if unknown else ""
    return f"İş kuralı Z3 ile İSPATLANDI: \"{rule}\" — {', '.join(proved[:6])} hiçbir tamsayı girdide değeri negatife düşürmüyor.{tail}"
