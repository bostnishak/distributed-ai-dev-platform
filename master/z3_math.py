"""Check a numeric answer with the Z3 solver: the model only writes the equations, the solver decides.

Equations are parsed from a small arithmetic grammar (never executed as code). A result counts only when it is unique.
"""

from __future__ import annotations

import ast
import json
import operator
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field, ValidationError

import gateway
import llm
from prompt_loader import load_prompt

_OPS: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Eq: operator.eq, ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
}
_TIMEOUT_MS = 3000


class Model(BaseModel):
    variables: dict[str, str] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list, max_length=20)
    ask: str = ""


def _term(node: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.Name) and node.id in env:
        return env[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_term(node.operand, env)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_term(node.left, env), _term(node.right, env))
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _OPS:
        return _OPS[type(node.ops[0])](_term(node.left, env), _term(node.comparators[0], env))
    raise ValueError("desteklenmeyen ifade")


def solve(model: Model) -> float | None:
    """The only value of `ask` that satisfies all constraints, else None (no solution, several, or not parsable)."""
    import z3

    if model.ask not in model.variables or not model.constraints or len(model.variables) > 12:
        return None
    env = {name: (z3.Int(name) if kind == "int" else z3.Real(name)) for name, kind in model.variables.items() if name.isidentifier()}
    solver = z3.Solver()
    solver.set("timeout", _TIMEOUT_MS)
    try:
        for text in model.constraints:
            solver.add(_term(ast.parse(text, mode="eval").body, env))
        if model.ask not in env or solver.check() != z3.sat:
            return None
        value = solver.model().eval(env[model.ask], model_completion=True)
        solver.add(env[model.ask] != value)
        if solver.check() != z3.unsat:
            return None
        return float(value.as_long() if z3.is_int_value(value) else value.as_fraction())
    except (SyntaxError, ValueError, TypeError, AttributeError, z3.Z3Exception, ZeroDivisionError):
        return None


async def _reasoning_chat(system: str, user: str, schema: dict, num_ctx: int) -> str:
    """The 9B reasoning model: the small master model writes wrong equations (gave a chicken four legs)."""
    try:
        res = await gateway.default_client.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], model="qwen3.5:9b",
                                                profile="extract", format_schema=schema, num_predict=600, num_ctx=num_ctx, timeout_s=180.0, feature="reasoning", max_retries=0)
    except Exception as exc:
        raise llm.LLMError(str(exc)) from exc
    return res.content


async def confirm(question: str, answer: str, chat: Callable[[str, str, dict, int], Awaitable[str]] | None = None) -> str:
    """A confirmation line when Z3's unique value appears in the drafted answer; empty when it cannot confirm."""
    chat = chat or _reasoning_chat
    try:
        parsed = Model.model_validate(json.loads(await chat(load_prompt("agent_equations.md"), question[:1500], Model.model_json_schema(), 4096)))
    except (llm.LLMError, ValidationError, ValueError):
        return ""
    value = solve(parsed)
    if value is None:
        return ""
    shown = str(int(value)) if value.is_integer() else f"{value:.4g}"
    tail = answer[-300:].replace(",", ".")
    if shown in tail:
        return f"\n\n> Z3 çözücüsüyle doğrulandı: {parsed.ask} = {shown}"
    return f"\n\n> Uyarı: denklemlerden Z3 {parsed.ask} = {shown} buluyor, yukarıdaki sonuçla uyuşmuyor. Denklemler: {'; '.join(parsed.constraints)}"
