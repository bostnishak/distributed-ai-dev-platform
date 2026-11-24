"""EPK-06: IDE Language Diagnostics (LSP), Safe Debug Adapter (DAP) & Multi-File Unified Diff Bridge."""

from __future__ import annotations

import ast
import difflib
import secrets
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ide", tags=["ide-bridge"])


def get_lsp_diagnostics(code: str, language: str = "python") -> dict[str, Any]:
    """Produce LSP-compatible diagnostics and outline symbols for editor integration."""
    diagnostics: list[dict[str, Any]] = []
    symbols: list[dict[str, Any]] = []
    if language.lower() == "python":
        try:
            tree = ast.parse(code or "")
        except SyntaxError as exc:
            diagnostics.append({
                "severity": "error",
                "line": (exc.lineno or 1),
                "col": (exc.offset or 1),
                "code": "E999",
                "message": exc.msg,
            })
            return {"ok": True, "language": language, "diagnostics": diagnostics, "symbols": symbols}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.append({
                    "name": node.name,
                    "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                    "line": node.lineno,
                })
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                diagnostics.append({
                    "severity": "warning",
                    "line": node.lineno,
                    "col": node.col_offset + 1,
                    "code": "S307",
                    "message": f"Güvensiz dinamik çağrı: {node.func.id}()",
                })
    else:
        for idx, line in enumerate((code or "").splitlines(), start=1):
            if "innerHTML" in line:
                diagnostics.append({
                    "severity": "warning",
                    "line": idx,
                    "col": line.index("innerHTML") + 1,
                    "code": "XSS01",
                    "message": "innerHTML yerine textContent veya sanitize edilmiş DOM kullanın.",
                })
    return {"ok": True, "language": language, "diagnostics": diagnostics, "symbols": symbols}


def create_dap_trace_session(code: str, breakpoints: list[int]) -> dict[str, Any]:
    """Create a deterministic DAP debug plan validating breakpoint lines against executable AST statements."""
    session_id = f"dap_{secrets.token_hex(6)}"
    executable_lines: set[int] = set()
    try:
        tree = ast.parse(code or "")
        for node in ast.walk(tree):
            if isinstance(node, ast.stmt) and hasattr(node, "lineno"):
                executable_lines.add(node.lineno)
    except SyntaxError as exc:
        return {"ok": False, "session_id": session_id, "error": f"SyntaxError line {exc.lineno}: {exc.msg}", "verified_breakpoints": []}
    verified = [{"line": bp, "verified": bp in executable_lines} for bp in sorted(set(breakpoints))]
    return {
        "ok": True,
        "session_id": session_id,
        "executable_line_count": len(executable_lines),
        "verified_breakpoints": verified,
        "state": "paused" if any(b["verified"] for b in verified) else "ready",
    }


def compute_multi_file_diff(files: list[dict[str, str]]) -> dict[str, Any]:
    """Generate unified diffs across multiple files for IDE multi-file review."""
    patches: list[dict[str, Any]] = []
    total_added = 0
    total_removed = 0
    for item in files:
        path = (item.get("path") or "untitled")
        before = (item.get("before") or "").splitlines(keepends=True)
        after = (item.get("after") or "").splitlines(keepends=True)
        diff_lines = list(difflib.unified_diff(before, after, fromfile=f"a/{path}", tofile=f"b/{path}"))
        added = sum(1 for ln in diff_lines if ln.startswith("+") and not ln.startswith("+++"))
        removed = sum(1 for ln in diff_lines if ln.startswith("-") and not ln.startswith("---"))
        total_added += added
        total_removed += removed
        patches.append({"path": path, "added": added, "removed": removed, "unified_diff": "".join(diff_lines)})
    return {"ok": True, "file_count": len(patches), "total_added": total_added, "total_removed": total_removed, "patches": patches}


class LspDiagnosticsRequest(BaseModel):
    code: str = Field(default="", max_length=120000)
    language: str = Field(default="python", max_length=32)


class DapSessionRequest(BaseModel):
    code: str = Field(default="", max_length=120000)
    breakpoints: list[int] = Field(default_factory=list)


class MultiDiffRequest(BaseModel):
    files: list[dict[str, str]] = Field(default_factory=list)


@router.post("/lsp/diagnostics")
async def api_lsp_diagnostics(body: LspDiagnosticsRequest):
    """Run LSP syntax/security diagnostics and extract outline symbols."""
    return get_lsp_diagnostics(body.code, body.language)


@router.post("/dap/session")
async def api_dap_session(body: DapSessionRequest):
    """Create a DAP debug session and verify breakpoint positions."""
    return create_dap_trace_session(body.code, body.breakpoints)


@router.post("/diff/multi")
async def api_multi_diff(body: MultiDiffRequest):
    """Compute unified multi-file diffs for IDE review."""
    return compute_multi_file_diff(body.files)
