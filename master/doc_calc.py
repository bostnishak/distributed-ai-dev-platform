"""Exact numbers for generated documents: the model supplies inputs and formulas, this module does the arithmetic.

Expressions are parsed with `ast` and only allow numbers, input names, + - * / ** % and a few pure functions, so a model-written
formula can never run code. Results are formatted Turkish-style (1.234,50) and substituted into the text as {key}.
"""

from __future__ import annotations

import ast
import math
import operator
import re
from typing import Any

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod}
_FUNCS = {"min": min, "max": max, "round": round, "abs": abs, "sum": lambda *a: sum(a), "ceil": math.ceil, "floor": math.floor}
_KEY_RE = re.compile(r"\{([^\W\d]\w*)\}")


def _eval(node: ast.AST, env: dict[str, float]) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in env:
        return env[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left, env), _eval(node.right, env)
        if isinstance(node.op, ast.Pow) and abs(right) > 12:
            raise ValueError("exponent too large")
        return float(_OPS[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return -_eval(node.operand, env) if isinstance(node.op, ast.USub) else _eval(node.operand, env)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS and not node.keywords:
        return float(_FUNCS[node.func.id](*[_eval(a, env) for a in node.args]))
    raise ValueError("unsupported expression")


def evaluate(expr: str, env: dict[str, float]) -> float:
    return _eval(ast.parse(str(expr).strip().lstrip("="), mode="eval").body, env)


def fmt_number(x: float, unit: str = "") -> str:
    """1234.5 -> '1.234,5'; whole numbers without decimals; unit appended."""
    text = f"{x:,.0f}" if abs(x - round(x)) < 1e-9 else f"{x:,.2f}".rstrip("0").rstrip(".")
    text = text.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{text} {unit}".strip()


def unscale(n: float, shown: dict[str, str]) -> float:
    """The model sometimes writes amounts in thousands (120 for 120.000 TL): a bare number that equals a computed value / 1000
    (or / 1e6) and is not itself a known value is restored to the exact computed figure."""
    values = list(getattr(shown, "numbers", {}).values())
    if not values or any(abs(v - n) < 1e-9 for v in values):
        return n
    for factor in (1000.0, 1_000_000.0):
        for v in values:
            if abs(v) >= factor and abs(v / factor - n) < max(0.006, abs(n) * 1e-6):
                return v
    return n


class Shown(dict):
    """Display strings by key; `numbers` keeps the numeric values so {expression} placeholders can be evaluated."""

    numbers: dict[str, float]


def run(calc: Any) -> tuple[dict[str, float], dict[str, str], list[dict[str, str]]]:
    """(numeric values, display strings, rows for a calc table) from {"inputs": [...], "outputs": [...]}; bad items are skipped."""
    values: dict[str, float] = {}
    shown: Shown = Shown()
    shown.numbers = values
    rows: list[dict[str, str]] = []
    if not isinstance(calc, dict):
        return values, shown, rows
    for item in (calc.get("inputs") or [])[:40]:
        if isinstance(item, dict) and re.fullmatch(r"[^\W\d]\w*", str(item.get("key", ""))) and isinstance(item.get("value"), (int, float)):
            key = str(item["key"])
            values[key] = float(item["value"])
            shown[key] = fmt_number(values[key], str(item.get("unit") or ""))
            rows.append({"key": key, "label": str(item.get("label") or key), "value": shown[key], "kind": "varsayım" if item.get("source") == "assumption" else "verilen"})
    for item in (calc.get("outputs") or [])[:40]:
        if not isinstance(item, dict) or not re.fullmatch(r"[^\W\d]\w*", str(item.get("key", ""))):
            continue
        try:
            key = str(item["key"])
            values[key] = evaluate(str(item.get("expr", "")), values)
        except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, TypeError):
            continue
        shown[key] = fmt_number(values[key], str(item.get("unit") or ""))
        rows.append({"key": key, "label": str(item.get("label") or key), "value": shown[key], "kind": "hesaplanan"})
    return values, shown, rows


_EXPR_RE = re.compile(r"\{([^{}]*[+\-*/()][^{}]*)\}")


def fill(text: str, shown: dict[str, str]) -> str:
    """Replace {key} with the computed display string. A {expression} such as {a/b} is evaluated with the known values;
    anything unknown becomes a fill-in blank so no invented number slips in. Markdown emphasis and doubled units are cleaned."""

    values = getattr(shown, "numbers", {})

    def expr(m: re.Match[str]) -> str:
        try:
            return fmt_number(evaluate(m.group(1), values))
        except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, TypeError):
            return "[................]"

    text = _EXPR_RE.sub(expr, str(text))
    text = _KEY_RE.sub(lambda m: shown.get(m.group(1), "[................]"), text)
    text = re.sub(r"\*\*|__", "", text)
    text = re.sub(r"\b(TL|ay|gün|adet)\s+\1\b", r"\1", text)
    return re.sub(r"%\s*%", "%", text)


def missing_keys(draft: dict[str, Any]) -> dict[str, str]:
    """{key: sentence it appears in} for {placeholders} in the draft's texts that have no value after evaluating its calc."""
    import json

    _, shown, _ = run(draft.get("calc"))
    found: dict[str, str] = {}
    for b in draft.get("blocks") or []:
        if not isinstance(b, dict):
            continue
        texts = [str(b.get("text") or "")] + [str(i) for i in b.get("items") or []] + [str(c) for r in b.get("rows") or [] if isinstance(r, list) for c in r]
        texts += [json.dumps(b.get("values") or [], ensure_ascii=False)] if b.get("type") == "chart" else []
        for t in texts:
            for m in _KEY_RE.finditer(t):
                if m.group(1) not in shown:
                    found.setdefault(m.group(1), t[:200])
    return found
