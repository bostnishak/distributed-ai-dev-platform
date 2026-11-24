"""EPK-15: Memory Contradiction Queue, User Resolution, Time-Decay Scoring & Consolidation."""

from __future__ import annotations

import math
import sqlite3
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import dbconn
import memory_engine
import user_profile

router = APIRouter(prefix="/api/memory", tags=["memory-conflicts"])


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("platform.db"))


def init_memory_conflicts_db() -> None:
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS memory_conflicts ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, category TEXT NOT NULL, "
            "fact_key TEXT NOT NULL, existing_value TEXT NOT NULL, candidate_value TEXT NOT NULL, "
            "status TEXT NOT NULL DEFAULT 'open', resolution TEXT NOT NULL DEFAULT '', "
            "created_at TEXT NOT NULL, resolved_at TEXT)"
        )


def score_memory_with_decay(confidence: float, age_days: float, half_life_days: float = 90.0) -> float:
    """Apply exponential half-life decay to semantic memory confidence."""
    lam = math.log(2.0) / max(1.0, half_life_days)
    return round(max(0.05, float(confidence) * math.exp(-lam * max(0.0, age_days))), 4)


def detect_and_queue_conflict(user_id: str, category: str, fact_key: str, candidate_value: str) -> dict[str, Any]:
    """Compare candidate fact against stored memory; enqueue contradiction if value differs."""
    init_memory_conflicts_db()
    uid = user_profile.valid_user_id(user_id)
    facts = memory_engine.list_semantic_facts(user_id=uid)
    existing = next((f for f in facts if f.get("category") == category and f.get("fact_key") == fact_key), None)
    clean_val = candidate_value.strip()
    if not existing or str(existing.get("fact_value") or "").strip().lower() == clean_val.lower():
        fact_id = memory_engine.upsert_semantic_fact(category, fact_key, clean_val, user_id=uid)
        return {"ok": True, "conflict_detected": False, "fact_id": fact_id}
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO memory_conflicts "
            "(user_id, category, fact_key, existing_value, candidate_value, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'open', ?)",
            (uid, category, fact_key, str(existing["fact_value"]), clean_val, now),
        )
        cid = int(cur.lastrowid or 0)
    return {
        "ok": True,
        "conflict_detected": True,
        "conflict_id": cid,
        "existing_value": existing["fact_value"],
        "candidate_value": clean_val,
    }


def list_conflicts(user_id: str, status: str | None = None) -> list[dict[str, Any]]:
    init_memory_conflicts_db()
    uid = user_profile.valid_user_id(user_id)
    with _connect() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM memory_conflicts WHERE user_id = ? AND status = ? ORDER BY id DESC",
                (uid, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memory_conflicts WHERE user_id = ? ORDER BY id DESC",
                (uid,),
            ).fetchall()
    return [dict(r) for r in rows]


def resolve_conflict(conflict_id: int, decision: str, user_id: str = "default") -> dict[str, Any]:
    """Resolve a queued memory contradiction (keep_existing | accept_new | merge)."""
    init_memory_conflicts_db()
    uid = user_profile.valid_user_id(user_id)
    if decision not in {"keep_existing", "accept_new", "merge"}:
        raise ValueError("Geçersiz çözüm kararı (keep_existing, accept_new veya merge olmalı).")
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM memory_conflicts WHERE id = ? AND user_id = ?",
            (conflict_id, uid),
        ).fetchone()
        if not row:
            raise KeyError(f"Çelişki kaydı bulunamadı: {conflict_id}")
        final_val = (
            str(row["existing_value"]) if decision == "keep_existing" else
            str(row["candidate_value"]) if decision == "accept_new" else
            f"{row['existing_value']} | {row['candidate_value']}"
        )
        memory_engine.upsert_semantic_fact(str(row["category"]), str(row["fact_key"]), final_val, user_id=uid)
        conn.execute(
            "UPDATE memory_conflicts SET status = 'resolved', resolution = ?, resolved_at = ? "
            "WHERE id = ? AND user_id = ?",
            (decision, now, conflict_id, uid),
        )
    return {"ok": True, "conflict_id": conflict_id, "decision": decision, "resolved_value": final_val}


def consolidate_user_memories(user_id: str, half_life_days: float = 90.0) -> dict[str, Any]:
    """Compute time-decayed relevance weights and provenance summary for all semantic memories."""
    uid = user_profile.valid_user_id(user_id)
    facts = memory_engine.list_semantic_facts(user_id=uid)
    now = datetime.now(UTC)
    scored: list[dict[str, Any]] = []
    for f in facts:
        try:
            updated = datetime.fromisoformat(str(f.get("updated_at") or now.isoformat()).replace("Z", "+00:00"))
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=UTC)
            age_days = max(0.0, (now - updated).total_seconds() / 86400.0)
        except ValueError:
            age_days = 0.0
        decayed = score_memory_with_decay(float(f.get("confidence", 1.0)), age_days, half_life_days)
        scored.append({"id": f["id"], "category": f["category"], "fact_key": f["fact_key"], "decayed_score": decayed})
    return {"ok": True, "user_id": uid, "memory_count": len(scored), "used_memory_ids": [s["id"] for s in scored], "scored": scored}


class ConflictDetectRequest(BaseModel):
    user_id: str = Field(default="default", max_length=64)
    category: str = Field(default="preference", max_length=40)
    fact_key: str = Field(..., min_length=1, max_length=80)
    candidate_value: str = Field(..., min_length=1, max_length=500)


class ConflictResolveRequest(BaseModel):
    decision: str = Field(..., pattern="^(keep_existing|accept_new|merge)$")
    user_id: str = Field(default="default", max_length=64)


class ConsolidateRequest(BaseModel):
    user_id: str = Field(default="default", max_length=64)
    half_life_days: float = Field(default=90.0, ge=1.0, le=3650.0)


@router.get("/conflicts")
async def api_list_conflicts(user_id: str = Query(default="default"), status: str | None = Query(default=None)):
    """List open or resolved memory contradictions for a user."""
    try:
        items = list_conflicts(user_id, status=status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "count": len(items), "conflicts": items}


@router.post("/conflicts/detect")
async def api_detect_conflict(body: ConflictDetectRequest):
    """Detect contradiction against stored semantic memory and enqueue if conflicting."""
    try:
        return detect_and_queue_conflict(body.user_id, body.category, body.fact_key, body.candidate_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/conflicts/{conflict_id}/resolve")
async def api_resolve_conflict(conflict_id: int, body: ConflictResolveRequest):
    """Resolve a queued memory contradiction with user confirmation."""
    try:
        return resolve_conflict(conflict_id, body.decision, user_id=body.user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/consolidate")
async def api_consolidate_memory(body: ConsolidateRequest):
    """Run half-life time-decay consolidation and return memory provenance IDs."""
    try:
        return consolidate_user_memories(body.user_id, half_life_days=body.half_life_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
