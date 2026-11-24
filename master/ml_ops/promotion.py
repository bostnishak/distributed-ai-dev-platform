"""EPK-31: Formal ML Model Promotion Gate, Eval Threshold Enforcement, Canary Split & Audit Rollback."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import dbconn
from audit_log import AuditTrail

router = APIRouter(prefix="/api/ml/models", tags=["ml-promotion"])


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("platform.db"))


def init_ml_promotions_db() -> None:
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS ml_model_promotions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, model_id TEXT NOT NULL, eval_score REAL NOT NULL, "
            "min_threshold REAL NOT NULL, stage TEXT NOT NULL, canary_pct INTEGER NOT NULL DEFAULT 0, "
            "actor TEXT NOT NULL DEFAULT 'admin', created_at TEXT NOT NULL)"
        )


def promote_model(
    model_id: str, eval_score: float, *, min_threshold: float = 0.80, canary_pct: int = 10, actor: str = "admin"
) -> dict[str, Any]:
    """Enforce eval threshold gate before promoting a model to canary/production."""
    init_ml_promotions_db()
    if eval_score < min_threshold:
        AuditTrail().append_event(
            actor=actor,
            action="ML_MODEL_PROMOTION_REJECTED",
            payload={"model_id": model_id, "eval_score": eval_score, "min_threshold": min_threshold},
        )
        raise ValueError(f"Model terfisi reddedildi: eval_score ({eval_score:.3f}) < eşik ({min_threshold:.3f}).")
    stage = "production" if canary_pct >= 100 else "canary"
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO ml_model_promotions (model_id, eval_score, min_threshold, stage, canary_pct, actor, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (model_id, float(eval_score), float(min_threshold), stage, canary_pct, actor, now),
        )
        pid = (cur.lastrowid or 0)
    AuditTrail().append_event(
        actor=actor,
        action="ML_MODEL_PROMOTED",
        payload={"promotion_id": pid, "model_id": model_id, "stage": stage, "canary_pct": canary_pct},
    )
    return {
        "ok": True,
        "promotion_id": pid,
        "model_id": model_id,
        "stage": stage,
        "canary_pct": canary_pct,
        "eval_score": eval_score,
        "created_at": now,
    }


def rollback_model(model_id: str, reason: str = "manual_rollback", actor: str = "admin") -> dict[str, Any]:
    """Revert a model's canary/production traffic to 0% with an immutable audit event."""
    init_ml_promotions_db()
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO ml_model_promotions (model_id, eval_score, min_threshold, stage, canary_pct, actor, created_at) "
            "VALUES (?, 0.0, 0.0, 'rolled_back', 0, ?, ?)",
            (model_id, actor, now),
        )
        pid = (cur.lastrowid or 0)
    AuditTrail().append_event(
        actor=actor,
        action="ML_MODEL_ROLLED_BACK",
        payload={"promotion_id": pid, "model_id": model_id, "reason": reason},
    )
    return {"ok": True, "promotion_id": pid, "model_id": model_id, "stage": "rolled_back", "canary_pct": 0, "reason": reason}


class PromoteModelRequest(BaseModel):
    eval_score: float = Field(..., ge=0.0, le=1.0)
    min_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    canary_pct: int = Field(default=10, ge=1, le=100)
    actor: str = Field(default="admin", max_length=64)


class RollbackModelRequest(BaseModel):
    reason: str = Field(default="canary_regression", max_length=256)
    actor: str = Field(default="admin", max_length=64)


@router.post("/{model_id}/promote")
async def api_promote_model(model_id: str, body: PromoteModelRequest):
    """Promote a model to canary or production only if it passes the eval threshold gate."""
    try:
        return promote_model(
            model_id, body.eval_score, min_threshold=body.min_threshold, canary_pct=body.canary_pct, actor=body.actor
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{model_id}/rollback")
async def api_rollback_model(model_id: str, body: RollbackModelRequest):
    """Roll back a promoted/canary model to 0% traffic with audit logging."""
    return rollback_model(model_id, reason=body.reason, actor=body.actor)
