"""EPK-18: Data Science Train/Test Leakage Guard & Sandboxed In-Memory SQL Analytics."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/studios/data", tags=["data-leakage-sql"])

_FORBIDDEN_SQL = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|DETACH|PRAGMA|REPLACE)\b", re.IGNORECASE)


def _row_sig(row: dict[str, Any], exclude: str) -> str:
    body = {k: v for k, v in sorted(row.items()) if k != exclude}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return abs(num / (dx * dy)) if dx > 1e-12 and dy > 1e-12 else 0.0


def detect_dataset_leakage(
    train_rows: list[dict[str, Any]], test_rows: list[dict[str, Any]], target_col: str
) -> dict[str, Any]:
    """Detect train/test duplicate row leakage and suspiciously high feature-target correlations."""
    train_sigs = {_row_sig(r, target_col) for r in train_rows}
    overlap = sum(1 for r in test_rows if _row_sig(r, target_col) in train_sigs)
    leaky_cols: list[dict[str, Any]] = []
    if train_rows and target_col in train_rows[0]:
        ys: list[float] = []
        valid_rows: list[dict[str, Any]] = []
        for r in train_rows:
            try:
                ys.append(float(r[target_col]))
                valid_rows.append(r)
            except (TypeError, ValueError, KeyError):
                continue
        for col in [c for c in train_rows[0] if c != target_col]:
            try:
                xs = [float(r[col]) for r in valid_rows]
            except (TypeError, ValueError, KeyError):
                continue
            corr = _pearson(xs, ys)
            if corr >= 0.995:
                leaky_cols.append({"column": col, "abs_pearson_r": round(corr, 4)})
    return {
        "ok": True,
        "leakage_detected": overlap > 0 or len(leaky_cols) > 0,
        "duplicate_test_rows": overlap,
        "leaky_features": leaky_cols,
    }


def run_inmemory_sql_analytics(rows: list[dict[str, Any]], sql: str) -> dict[str, Any]:
    """Load JSON tabular rows into ephemeral SQLite :memory: table `data` and run read-only SELECT."""
    clean_sql = (sql or "").strip().rstrip(";")
    if not clean_sql.lower().startswith("select") or _FORBIDDEN_SQL.search(clean_sql):
        raise ValueError("Yalnızca salt-okunur SELECT sorgularına izin verilir.")
    if not rows:
        return {"ok": True, "columns": [], "row_count": 0, "rows": []}
    cols = [re.sub(r"[^A-Za-z0-9_]", "_", c) or f"col_{i}" for i, c in enumerate(rows[0].keys())]
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        col_defs = ", ".join(f'"{c}"' for c in cols)
        conn.execute(f"CREATE TABLE data ({col_defs})")
        ph = ", ".join("?" for _ in cols)
        orig_keys = list(rows[0].keys())
        insert_stmt = "".join(["INSERT INTO data (", col_defs, ") VALUES (", ph, ")"])
        conn.executemany(
            insert_stmt,
            [tuple(r.get(k) for k in orig_keys) for r in rows[:5000]],
        )
        cur = conn.execute(clean_sql)
        out_rows = [dict(r) for r in cur.fetchmany(500)]
        out_cols = [d[0] for d in (cur.description or [])]
        return {"ok": True, "columns": out_cols, "row_count": len(out_rows), "rows": out_rows}
    except sqlite3.Error as exc:
        raise ValueError(f"SQL sorgu hatası: {exc}") from exc
    finally:
        conn.close()


class LeakageCheckRequest(BaseModel):
    train_rows: list[dict[str, Any]] = Field(default_factory=list)
    test_rows: list[dict[str, Any]] = Field(default_factory=list)
    target_col: str = Field(..., min_length=1, max_length=64)


class SqlAnalyticsRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)
    sql: str = Field(default="SELECT COUNT(*) AS total FROM data", min_length=6, max_length=4000)


@router.post("/leakage-check")
async def api_leakage_check(body: LeakageCheckRequest):
    """Detect train/test duplicate overlap and target leakage features."""
    return detect_dataset_leakage(body.train_rows, body.test_rows, body.target_col)


@router.post("/sql-query")
async def api_sql_analytics(body: SqlAnalyticsRequest):
    """Execute read-only SELECT analytics queries over in-memory JSON tabular rows."""
    try:
        return run_inmemory_sql_analytics(body.rows, body.sql)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
