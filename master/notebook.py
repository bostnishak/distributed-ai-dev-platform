"""EPK-33: Stateful Cell-Based Notebook Engine with Safe AST Execution & Jupyter .ipynb v4.5 Import/Export."""

from __future__ import annotations

import ast
import json
import math
import operator
import secrets
import sqlite3
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import dbconn
import user_profile

router = APIRouter(prefix="/api/notebooks", tags=["notebooks"])

_SAFE_BIN: dict[type[ast.operator], Any] = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
}
_SAFE_UNARY: dict[type[ast.unaryop], Any] = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_SAFE_FUNCS: dict[str, Any] = {
    "abs": abs, "round": round, "min": min, "max": max, "sum": sum, "len": len, "sqrt": math.sqrt,
}


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("platform.db"))


def init_notebooks_db() -> None:
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS notebooks ("
            "notebook_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, title TEXT NOT NULL, "
            "cells_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )


def _eval_ast_expr(node: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in env:
        return env[node.id]
    if isinstance(node, ast.List):
        return [_eval_ast_expr(el, env) for el in node.elts]
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_BIN:
        return _SAFE_BIN[type(node.op)](_eval_ast_expr(node.left, env), _eval_ast_expr(node.right, env))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_UNARY:
        return _SAFE_UNARY[type(node.op)](_eval_ast_expr(node.operand, env))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _SAFE_FUNCS:
        return _SAFE_FUNCS[node.func.id](*[_eval_ast_expr(a, env) for a in node.args])
    raise ValueError(f"Desteklenmeyen veya izin verilmeyen ifade: {type(node).__name__}")


def execute_safe_cell(source: str) -> dict[str, Any]:
    """Execute safe deterministic notebook cell statements (assignments, print, math expressions) without eval/exec."""
    stdout_lines: list[str] = []
    env: dict[str, Any] = {}
    last_val: Any = None
    try:
        tree = ast.parse(source or "")
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                env[stmt.targets[0].id] = _eval_ast_expr(stmt.value, env)
            elif isinstance(stmt, ast.Expr):
                if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == "print":
                    args = [str(_eval_ast_expr(a, env)) for a in stmt.value.args]
                    stdout_lines.append(" ".join(args))
                else:
                    last_val = _eval_ast_expr(stmt.value, env)
            else:
                raise ValueError(f"Güvenlik nedeniyle bu ifade tipi engellendi: {type(stmt).__name__}")
    except (SyntaxError, ValueError, ZeroDivisionError, TypeError) as exc:
        return {"ok": False, "stdout": "\n".join(stdout_lines), "result": None, "error": str(exc)}
    return {"ok": True, "stdout": "\n".join(stdout_lines), "result": last_val, "error": ""}


def create_notebook(user_id: str, title: str, cells: list[dict[str, Any]]) -> dict[str, Any]:
    init_notebooks_db()
    uid = user_profile.valid_user_id(user_id)
    nb_id = f"nb_{secrets.token_hex(6)}"
    now = datetime.now(UTC).isoformat()
    norm_cells = [
        {"cell_type": str(c.get("cell_type") or "code"), "source": str(c.get("source") or ""), "outputs": list(c.get("outputs") or [])}
        for c in cells
    ]
    with _connect() as conn:
        conn.execute(
            "INSERT INTO notebooks (notebook_id, user_id, title, cells_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (nb_id, uid, title.strip() or "Yeni Defter", json.dumps(norm_cells, ensure_ascii=False), now, now),
        )
    return {"ok": True, "notebook_id": nb_id, "user_id": uid, "title": title.strip() or "Yeni Defter", "cells": norm_cells}


def list_notebooks(user_id: str) -> list[dict[str, Any]]:
    init_notebooks_db()
    uid = user_profile.valid_user_id(user_id)
    with _connect() as conn:
        rows = conn.execute(
            "SELECT notebook_id, user_id, title, cells_json, created_at, updated_at "
            "FROM notebooks WHERE user_id = ? ORDER BY updated_at DESC",
            (uid,),
        ).fetchall()
    return [{**dict(r), "cells": json.loads(r["cells_json"])} for r in rows]


def run_notebook_cell(notebook_id: str, user_id: str, cell_index: int) -> dict[str, Any]:
    init_notebooks_db()
    uid = user_profile.valid_user_id(user_id)
    with _connect() as conn:
        row = conn.execute(
            "SELECT title, cells_json FROM notebooks WHERE notebook_id = ? AND user_id = ?",
            (notebook_id, uid),
        ).fetchone()
        if not row:
            raise KeyError(f"Defter bulunamadı: {notebook_id}")
        cells: list[dict[str, Any]] = json.loads(row["cells_json"])
        if cell_index < 0 or cell_index >= len(cells):
            raise IndexError("Geçersiz hücre indeksi.")
        cell = cells[cell_index]
        exec_res = execute_safe_cell(str(cell.get("source") or "")) if cell.get("cell_type") == "code" else {"ok": True, "stdout": "", "result": cell.get("source"), "error": ""}
        cell["outputs"] = [exec_res]
        conn.execute(
            "UPDATE notebooks SET cells_json = ?, updated_at = ? WHERE notebook_id = ? AND user_id = ?",
            (json.dumps(cells, ensure_ascii=False), datetime.now(UTC).isoformat(), notebook_id, uid),
        )
    return {"ok": exec_res["ok"], "notebook_id": notebook_id, "cell_index": cell_index, "output": exec_res}


def export_ipynb_dict(notebook_id: str, user_id: str) -> dict[str, Any]:
    init_notebooks_db()
    uid = user_profile.valid_user_id(user_id)
    with _connect() as conn:
        row = conn.execute(
            "SELECT title, cells_json FROM notebooks WHERE notebook_id = ? AND user_id = ?",
            (notebook_id, uid),
        ).fetchone()
    if not row:
        raise KeyError(f"Defter bulunamadı: {notebook_id}")
    raw_cells: list[dict[str, Any]] = json.loads(row["cells_json"])
    nb_cells = [
        {
            "cell_type": c.get("cell_type", "code"),
            "metadata": {},
            "source": str(c.get("source") or "").splitlines(keepends=True),
            **({"execution_count": i + 1, "outputs": c.get("outputs", [])} if c.get("cell_type") == "code" else {}),
        }
        for i, c in enumerate(raw_cells)
    ]
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"title": row["title"], "kernelspec": {"name": "python3", "display_name": "Python 3 (DADP)"}},
        "cells": nb_cells,
    }


def import_ipynb_dict(user_id: str, ipynb: dict[str, Any]) -> dict[str, Any]:
    if int(ipynb.get("nbformat", 0)) != 4 or not isinstance(ipynb.get("cells"), list):
        raise ValueError("Geçersiz .ipynb v4 biçimi.")
    title = str((ipynb.get("metadata") or {}).get("title") or "İçe Aktarılan Defter")
    cells = [
        {
            "cell_type": str(c.get("cell_type") or "code"),
            "source": "".join(c.get("source") or []) if isinstance(c.get("source"), list) else str(c.get("source") or ""),
            "outputs": list(c.get("outputs") or []),
        }
        for c in ipynb["cells"]
        if isinstance(c, dict)
    ]
    return create_notebook(user_id, title, cells)


class CreateNotebookRequest(BaseModel):
    user_id: str = Field(default="default", max_length=64)
    title: str = Field(default="Yeni Defter", max_length=120)
    cells: list[dict[str, Any]] = Field(default_factory=list)


class RunCellRequest(BaseModel):
    user_id: str = Field(default="default", max_length=64)
    cell_index: int = Field(default=0, ge=0, le=500)


class ImportIpynbRequest(BaseModel):
    user_id: str = Field(default="default", max_length=64)
    ipynb: dict[str, Any]


@router.get("")
async def api_list_notebooks(user_id: str = Query(default="default")):
    """List persistent stateful notebooks for a user."""
    try:
        items = list_notebooks(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "count": len(items), "notebooks": items}


@router.post("")
async def api_create_notebook(body: CreateNotebookRequest):
    """Create a new stateful code/markdown notebook."""
    try:
        return create_notebook(body.user_id, body.title, body.cells)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{notebook_id}/run")
async def api_run_notebook_cell(notebook_id: str, body: RunCellRequest):
    """Execute a notebook cell safely and store captured outputs."""
    try:
        return run_notebook_cell(notebook_id, body.user_id, body.cell_index)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IndexError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{notebook_id}/export.ipynb")
async def api_export_ipynb(notebook_id: str, user_id: str = Query(default="default")):
    """Export a notebook in standard Jupyter nbformat v4.5 JSON."""
    try:
        return export_ipynb_dict(notebook_id, user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/import-ipynb")
async def api_import_ipynb(body: ImportIpynbRequest):
    """Import a Jupyter .ipynb v4 document into persistent notebook storage."""
    try:
        return import_ipynb_dict(body.user_id, body.ipynb)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
