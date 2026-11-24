"""ORC-08, ORC-09, ORC-10: Unified Tool Registry, Side-Effect Approval Gate & Bounded ReAct Loop."""

from __future__ import annotations

import ast
import inspect
import json
import math
import operator
import sqlite3
import subprocess
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

import audit_log

SIDE_EFFECT_CLASSES = frozenset({"read_only", "write", "network", "expensive"})
APPROVAL_REQUIRED_CLASSES = frozenset({"write", "network", "expensive"})

_SAFE_BINOPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_SAFE_UNARYOPS: dict[type, Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_SAFE_FUNCS: dict[str, Callable[..., float]] = {
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "pow": pow,
}


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    side_effect: str  # read_only | write | network | expensive
    handler: Callable[[dict[str, Any]], Any | Awaitable[Any]]
    timeout_s: float = 30.0

    def to_ollama_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }


@dataclass
class ToolResult:
    tool: str
    status: str  # ok | error | approval_required
    output: Any = None
    error: str = ""
    side_effect: str = "read_only"
    latency_ms: int = 0


def _validate_args(schema: dict[str, Any], args: dict[str, Any]) -> str | None:
    if not isinstance(args, dict):
        return "Argümanlar sözlük (JSON object) olmalıdır."
    required = schema.get("required") or []
    for req in required:
        if req not in args or args[req] is None:
            return f"Eksik zorunlu argüman: {req}"
    props = schema.get("properties") or {}
    type_map = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list, "object": dict}
    for key, val in args.items():
        if key not in props:
            continue
        expected = props[key].get("type")
        if expected in type_map and not isinstance(val, type_map[expected]):
            return f"Argüman '{key}' tipi geçersiz (beklenen: {expected})."
        enum_vals = props[key].get("enum")
        if enum_vals and val not in enum_vals:
            return f"Argüman '{key}' izin verilen değerlerden biri değil: {enum_vals}"
    return None


class ToolRegistry:
    """ORC-08 & ORC-09: Schema-validated tool registry with side-effect approval gate and audit logging."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.side_effect not in SIDE_EFFECT_CLASSES:
            raise ValueError(f"Geçersiz side_effect sınıfı: {spec.side_effect}")
        self._tools[spec.name] = spec

    def has(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def list_specs(self) -> list[dict[str, Any]]:
        return [
            {
                "name": s.name,
                "description": s.description,
                "side_effect": s.side_effect,
                "parameters": s.parameters_schema,
            }
            for s in self._tools.values()
        ]

    def ollama_tools(self, names: list[str] | None = None) -> list[dict[str, Any]]:
        selected = [self._tools[n] for n in names if n in self._tools] if names else list(self._tools.values())
        return [s.to_ollama_schema() for s in selected]

    async def execute(
        self,
        name: str,
        args: dict[str, Any],
        *,
        approval_granted: bool = False,
        actor: str = "user",
    ) -> ToolResult:
        spec = self._tools.get(name)
        if not spec:
            return ToolResult(tool=name, status="error", error=f"Bilinmeyen araç: {name}")

        err = _validate_args(spec.parameters_schema, args)
        if err:
            return ToolResult(tool=name, status="error", error=err, side_effect=spec.side_effect)

        # ORC-09: Side-effect gate
        if spec.side_effect in APPROVAL_REQUIRED_CLASSES and not approval_granted:
            audit_log.AuditTrail().append_event(
                actor=actor,
                action="tool_approval_required",
                payload={"tool": name, "status": "blocked", "side_effect": spec.side_effect, "arg_keys": sorted(args.keys())},
            )
            return ToolResult(
                tool=name,
                status="approval_required",
                error=f"'{name}' aracı ({spec.side_effect}) çalıştırılmadan önce kullanıcı onayı gerektirir.",
                side_effect=spec.side_effect,
            )

        t0 = time.perf_counter()
        try:
            res = spec.handler(args)
            if inspect.isawaitable(res):
                res = await res
            ms = int((time.perf_counter() - t0) * 1000)
            audit_log.AuditTrail().append_event(
                actor=actor,
                action="tool_execute",
                payload={"tool": name, "status": "ok", "side_effect": spec.side_effect, "latency_ms": ms},
            )
            return ToolResult(tool=name, status="ok", output=res, side_effect=spec.side_effect, latency_ms=ms)
        except (
            OSError,
            RuntimeError,
            ValueError,
            TypeError,
            LookupError,
            ArithmeticError,
            AttributeError,
            ImportError,
            SyntaxError,
            sqlite3.Error,
            subprocess.SubprocessError,
            httpx.HTTPError,
        ) as exc:
            ms = int((time.perf_counter() - t0) * 1000)
            audit_log.AuditTrail().append_event(
                actor=actor,
                action="tool_execute",
                payload={"tool": name, "status": "error", "error": str(exc)[:200]},
            )
            return ToolResult(tool=name, status="error", error=str(exc), side_effect=spec.side_effect, latency_ms=ms)


# ---------------------------------------------------------------- ORC-10 Bounded ReAct Loop

@dataclass
class ReActOutcome:
    final_answer: str
    steps_taken: int
    stopped_reason: str  # finished | max_steps | loop_detected | approval_required | timeout
    tool_trace: list[dict[str, Any]] = field(default_factory=list)


async def run_react_loop(
    decide_next: Callable[[list[dict[str, Any]]], Awaitable[dict[str, Any]]],
    registry: ToolRegistry,
    *,
    max_steps: int = 8,
    max_wall_s: float = 60.0,
    approval_granted: bool = False,
    actor: str = "user",
) -> ReActOutcome:
    """ORC-10: Bounded tool loop with wall-clock cap and repeated-call loop detector."""
    t0 = time.monotonic()
    history: list[dict[str, Any]] = []
    seen_calls: dict[str, int] = {}

    for step in range(1, max_steps + 1):
        if time.monotonic() - t0 > max_wall_s:
            return ReActOutcome(
                final_answer="Araç yürütme zaman sınırı doldu; toplanan sonuçlar özetlendi.",
                steps_taken=step - 1,
                stopped_reason="timeout",
                tool_trace=history,
            )

        decision = await decide_next(history)
        if decision.get("done") or not decision.get("tool"):
            return ReActOutcome(
                final_answer=str(decision.get("answer") or ""),
                steps_taken=step - 1,
                stopped_reason="finished",
                tool_trace=history,
            )

        tool_name = str(decision["tool"])
        args = dict(decision.get("args") or {})
        sig = f"{tool_name}:{json.dumps(args, sort_keys=True, ensure_ascii=False)}"
        seen_calls[sig] = seen_calls.get(sig, 0) + 1
        if seen_calls[sig] >= 2:
            return ReActOutcome(
                final_answer="Aynı araç çağrısı tekrarlandığı için döngü güvenli biçimde sonlandırıldı.",
                steps_taken=step - 1,
                stopped_reason="loop_detected",
                tool_trace=history,
            )

        tr = await registry.execute(tool_name, args, approval_granted=approval_granted, actor=actor)
        history.append({
            "step": step,
            "tool": tool_name,
            "args": args,
            "status": tr.status,
            "output": tr.output,
            "error": tr.error,
        })
        if tr.status == "approval_required":
            return ReActOutcome(
                final_answer=tr.error,
                steps_taken=step,
                stopped_reason="approval_required",
                tool_trace=history,
            )

    return ReActOutcome(
        final_answer="Maksimum araç adım sınırına ulaşıldı; ara bulgular derlendi.",
        steps_taken=max_steps,
        stopped_reason="max_steps",
        tool_trace=history,
    )


# ---------------------------------------------------------------- Built-in Safe Tools

def _safe_eval_expr(expr: str) -> float:
    node = ast.parse(expr.strip(), mode="eval")

    def _eval(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in _SAFE_BINOPS:
            return _SAFE_BINOPS[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _SAFE_UNARYOPS:
            return _SAFE_UNARYOPS[type(n.op)](_eval(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _SAFE_FUNCS:
            return float(_SAFE_FUNCS[n.func.id](*[_eval(a) for a in n.args]))
        raise ValueError("Desteklenmeyen matematiksel ifade.")

    return _eval(node)


def _tool_calculator(args: dict[str, Any]) -> dict[str, Any]:
    val = _safe_eval_expr(str(args["expression"]))
    return {"expression": args["expression"], "result": round(val, 8) if not val.is_integer() else int(val)}


def _tool_python_ast_check(args: dict[str, Any]) -> dict[str, Any]:
    code = str(args["code"])
    try:
        ast.parse(code)
        return {"valid": True, "lines": len(code.splitlines())}
    except SyntaxError as exc:
        return {"valid": False, "error": f"Satır {exc.lineno}: {exc.msg}"}


def _tool_file_convert_info(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "supported_conversions": ["pdf->docx", "pdf->pptx", "docx->pdf", "pptx->pdf", "zip->extract", "dir->zip"],
        "requested": str(args.get("operation") or ""),
    }


def _tool_sandbox_info(args: dict[str, Any]) -> dict[str, Any]:
    import sandbox

    return sandbox.status()


def _tool_memory_lookup(args: dict[str, Any]) -> dict[str, Any]:
    import memory_engine

    user_id = str(args.get("user_id") or "default")
    facts = memory_engine.list_semantic_facts(user_id=user_id)
    return {"count": len(facts), "memories": facts[:10]}


def build_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(
        ToolSpec(
            name="calculator",
            description="Deterministik matematiksel ifadeleri güvenli AST ile hesaplar.",
            parameters_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
            side_effect="read_only",
            handler=_tool_calculator,
        )
    )
    reg.register(
        ToolSpec(
            name="python_ast_check",
            description="Python kodunun sözdizimini AST ile doğrular.",
            parameters_schema={
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
            side_effect="read_only",
            handler=_tool_python_ast_check,
        )
    )
    reg.register(
        ToolSpec(
            name="file_convert_info",
            description="Desteklenen çift yönlü dosya dönüştürme ve arşiv yeteneklerini döner.",
            parameters_schema={"type": "object", "properties": {"operation": {"type": "string"}}},
            side_effect="read_only",
            handler=_tool_file_convert_info,
        )
    )
    reg.register(
        ToolSpec(
            name="sandbox_info",
            description="Docker kod çalıştırma sandbox durumunu raporlar.",
            parameters_schema={"type": "object", "properties": {}},
            side_effect="read_only",
            handler=_tool_sandbox_info,
        )
    )
    reg.register(
        ToolSpec(
            name="memory_lookup",
            description="Kullanıcı hafıza kayıtlarını sorgular.",
            parameters_schema={"type": "object", "properties": {"user_id": {"type": "string"}}},
            side_effect="read_only",
            handler=_tool_memory_lookup,
        )
    )
    reg.register(
        ToolSpec(
            name="workspace_write_file",
            description="Çalışma alanına dosya yazar (yan etkili - onay gerektirir).",
            parameters_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
            side_effect="write",
            handler=lambda a: {"written": a["path"], "bytes": len(str(a["content"]))},
        )
    )
    return reg


default_registry = build_default_registry()
