"""EPK-32: Usage Accounting (Tokens, Latency, Wh Energy Ledger) & Daily Hard/Soft Quota Enforcement."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import dbconn
import user_profile

router = APIRouter(prefix="/api/accounting", tags=["accounting"])

DEFAULT_DAILY_TOKENS = 250_000
DEFAULT_DAILY_ENERGY_WH = 500.0


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("platform.db"))


def init_accounting_db() -> None:
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS accounting_ledger ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, model TEXT NOT NULL, "
            "tokens_in INTEGER NOT NULL DEFAULT 0, tokens_out INTEGER NOT NULL DEFAULT 0, "
            "latency_ms INTEGER NOT NULL DEFAULT 0, energy_wh REAL NOT NULL DEFAULT 0.0, "
            "day_utc TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS user_quotas ("
            "user_id TEXT PRIMARY KEY, daily_token_limit INTEGER NOT NULL DEFAULT 250000, "
            "daily_energy_wh_limit REAL NOT NULL DEFAULT 500.0, hard_enforce INTEGER NOT NULL DEFAULT 1, "
            "updated_at TEXT NOT NULL)"
        )


def estimate_energy_wh(tokens_total: int, latency_ms: int, watts: float = 120.0) -> float:
    """Estimate local GPU/CPU Watt-hours consumed from latency and token throughput."""
    sec = max(0.05, latency_ms / 1000.0)
    base_wh = (watts * sec) / 3600.0
    tok_wh = tokens_total * 0.00015
    return round(max(base_wh, tok_wh), 5)


def set_user_quota(
    user_id: str, *, daily_token_limit: int = DEFAULT_DAILY_TOKENS, daily_energy_wh_limit: float = DEFAULT_DAILY_ENERGY_WH, hard_enforce: bool = True
) -> dict[str, Any]:
    init_accounting_db()
    uid = user_profile.valid_user_id(user_id)
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_quotas (user_id, daily_token_limit, daily_energy_wh_limit, hard_enforce, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (uid, int(daily_token_limit), float(daily_energy_wh_limit), 1 if hard_enforce else 0, now),
        )
    return {
        "ok": True,
        "user_id": uid,
        "daily_token_limit": daily_token_limit,
        "daily_energy_wh_limit": daily_energy_wh_limit,
        "hard_enforce": hard_enforce,
    }


def get_daily_report(user_id: str, day_utc: str | None = None) -> dict[str, Any]:
    init_accounting_db()
    uid = user_profile.valid_user_id(user_id)
    day = day_utc or datetime.now(UTC).strftime("%Y-%m-%d")
    with _connect() as conn:
        qrow = conn.execute(
            "SELECT daily_token_limit, daily_energy_wh_limit, hard_enforce FROM user_quotas WHERE user_id = ?",
            (uid,),
        ).fetchone()
        srow = conn.execute(
            "SELECT COUNT(*) AS calls, COALESCE(SUM(tokens_in), 0) AS t_in, COALESCE(SUM(tokens_out), 0) AS t_out, "
            "COALESCE(SUM(latency_ms), 0) AS lat_ms, COALESCE(SUM(energy_wh), 0.0) AS wh "
            "FROM accounting_ledger WHERE user_id = ? AND day_utc = ?",
            (uid, day),
        ).fetchone()
    tok_lim = int(qrow["daily_token_limit"]) if qrow else DEFAULT_DAILY_TOKENS
    wh_lim = float(qrow["daily_energy_wh_limit"]) if qrow else DEFAULT_DAILY_ENERGY_WH
    hard = bool(qrow["hard_enforce"]) if qrow else True
    used_tokens = int(srow["t_in"]) + int(srow["t_out"])
    used_wh = round(float(srow["wh"]), 4)
    return {
        "ok": True,
        "user_id": uid,
        "day_utc": day,
        "calls": int(srow["calls"]),
        "tokens_in": int(srow["t_in"]),
        "tokens_out": int(srow["t_out"]),
        "tokens_total": used_tokens,
        "latency_ms_total": int(srow["lat_ms"]),
        "energy_wh_total": used_wh,
        "quota": {
            "daily_token_limit": tok_lim,
            "daily_energy_wh_limit": wh_lim,
            "hard_enforce": hard,
            "token_utilization_pct": round((used_tokens / max(1, tok_lim)) * 100.0, 2),
        },
    }


def record_usage_entry(user_id: str, model: str, tokens_in: int, tokens_out: int, latency_ms: int) -> dict[str, Any]:
    """Record usage after enforcing daily hard quotas (raises HTTPException 429 if exceeded)."""
    init_accounting_db()
    uid = user_profile.valid_user_id(user_id)
    now = datetime.now(UTC)
    day = now.strftime("%Y-%m-%d")
    report = get_daily_report(uid, day)
    wh = estimate_energy_wh(tokens_in + tokens_out, latency_ms)
    projected_tokens = report["tokens_total"] + tokens_in + tokens_out
    projected_wh = report["energy_wh_total"] + wh
    q = report["quota"]
    if q["hard_enforce"] and (projected_tokens > q["daily_token_limit"] or projected_wh > q["daily_energy_wh_limit"]):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_quota_exceeded",
                "user_id": uid,
                "projected_tokens": projected_tokens,
                "daily_token_limit": q["daily_token_limit"],
                "projected_energy_wh": round(projected_wh, 4),
                "daily_energy_wh_limit": q["daily_energy_wh_limit"],
            },
        )
    with _connect() as conn:
        conn.execute(
            "INSERT INTO accounting_ledger (user_id, model, tokens_in, tokens_out, latency_ms, energy_wh, day_utc, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, model.strip()[:80], int(tokens_in), int(tokens_out), int(latency_ms), wh, day, now.isoformat()),
        )
    return {"ok": True, "user_id": uid, "day_utc": day, "energy_wh": wh, "tokens_total_today": projected_tokens}


class RecordUsageRequest(BaseModel):
    user_id: str = Field(default="default", max_length=64)
    model: str = Field(default="qwen3.5:4b", max_length=80)
    tokens_in: int = Field(default=100, ge=0, le=10_000_000)
    tokens_out: int = Field(default=100, ge=0, le=10_000_000)
    latency_ms: int = Field(default=500, ge=0, le=600_000)


class QuotaUpdateRequest(BaseModel):
    daily_token_limit: int = Field(default=DEFAULT_DAILY_TOKENS, ge=1, le=100_000_000)
    daily_energy_wh_limit: float = Field(default=DEFAULT_DAILY_ENERGY_WH, ge=0.01, le=100_000.0)
    hard_enforce: bool = True


@router.post("/record")
async def api_record_accounting(body: RecordUsageRequest):
    """Record token, latency, and Wh energy consumption with hard daily quota enforcement."""
    try:
        return record_usage_entry(body.user_id, body.model, body.tokens_in, body.tokens_out, body.latency_ms)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/quotas/{user_id}")
async def api_set_quota(user_id: str, body: QuotaUpdateRequest):
    """Configure daily token and energy Wh quotas for a user."""
    try:
        return set_user_quota(
            user_id,
            daily_token_limit=body.daily_token_limit,
            daily_energy_wh_limit=body.daily_energy_wh_limit,
            hard_enforce=body.hard_enforce,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/report/{user_id}")
async def api_accounting_report(user_id: str, day_utc: str | None = None):
    """Return daily token, latency, energy Wh, and quota utilization report."""
    try:
        return get_daily_report(user_id, day_utc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
