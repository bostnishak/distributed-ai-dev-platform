"""EPK-10 & EPK-30: High Availability SQLite Leader Lease, Rolling-Upgrade Drain & Idempotent Task Commit."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

import dbconn
from ha.pg_adapter import detect_ha_backend

router = APIRouter(prefix="/api/ha", tags=["high-availability"])


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("platform.db"))


def init_ha_db() -> None:
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS ha_leases ("
            "lease_key TEXT PRIMARY KEY, leader_id TEXT NOT NULL, expires_at TEXT NOT NULL, "
            "term INTEGER NOT NULL DEFAULT 1, draining INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS idempotent_results ("
            "idempotency_key TEXT PRIMARY KEY, task_id TEXT NOT NULL, agent_id TEXT NOT NULL, "
            "result_hash TEXT NOT NULL, committed_at TEXT NOT NULL)"
        )


def acquire_or_renew_lease(node_id: str, lease_key: str = "master-primary", ttl_s: int = 15) -> dict[str, Any]:
    """Attempt to acquire or renew the HA leader lease; fails over cleanly when previous lease expired or drained."""
    init_ha_db()
    now = datetime.now(UTC)
    new_exp = (now + timedelta(seconds=max(3, min(ttl_s, 300)))).isoformat()
    with _connect() as conn:
        row = conn.execute(
            "SELECT leader_id, expires_at, term, draining FROM ha_leases WHERE lease_key = ?",
            (lease_key,),
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO ha_leases (lease_key, leader_id, expires_at, term, draining, updated_at) "
                "VALUES (?, ?, ?, 1, 0, ?)",
                (lease_key, node_id, new_exp, now.isoformat()),
            )
            return {"acquired": True, "leader_id": node_id, "term": 1, "expires_at": new_exp}
        expired = datetime.fromisoformat(str(row["expires_at"])) <= now
        same_leader = str(row["leader_id"]) == node_id
        is_draining = bool(row["draining"])
        if same_leader and not is_draining:
            conn.execute(
                "UPDATE ha_leases SET expires_at = ?, updated_at = ? WHERE lease_key = ?",
                (new_exp, now.isoformat(), lease_key),
            )
            return {"acquired": True, "leader_id": node_id, "term": int(row["term"]), "expires_at": new_exp}
        if expired or is_draining:
            next_term = int(row["term"]) + 1
            conn.execute(
                "UPDATE ha_leases SET leader_id = ?, expires_at = ?, term = ?, draining = 0, updated_at = ? "
                "WHERE lease_key = ?",
                (node_id, new_exp, next_term, now.isoformat(), lease_key),
            )
            return {"acquired": True, "leader_id": node_id, "term": next_term, "expires_at": new_exp, "failover": True}
        return {
            "acquired": False,
            "leader_id": str(row["leader_id"]),
            "term": int(row["term"]),
            "expires_at": str(row["expires_at"]),
        }


def drain_leader_node(node_id: str, lease_key: str = "master-primary") -> dict[str, Any]:
    """Mark the active leader as draining so standby masters can take over immediately for rolling upgrade."""
    init_ha_db()
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        updated = conn.execute(
            "UPDATE ha_leases SET draining = 1, updated_at = ? WHERE lease_key = ? AND leader_id = ?",
            (now, lease_key, node_id),
        ).rowcount
    return {"ok": True, "node_id": node_id, "drained": updated > 0}


def get_ha_status(lease_key: str = "master-primary") -> dict[str, Any]:
    init_ha_db()
    backend = detect_ha_backend()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM ha_leases WHERE lease_key = ?", (lease_key,)).fetchone()
    if not row:
        return {"ok": True, "lease_key": lease_key, "leader": None, "term": 0, "draining": False, "backend": backend}
    return {
        "ok": True,
        "lease_key": lease_key,
        "leader": row["leader_id"],
        "term": int(row["term"]),
        "draining": bool(row["draining"]),
        "expires_at": row["expires_at"],
        "backend": backend,
    }


def commit_idempotent_result(idempotency_key: str, task_id: str, agent_id: str, payload: str) -> dict[str, Any]:
    """Commit a task result exactly once; duplicate retries return duplicate=True with original hash."""
    init_ha_db()
    r_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        existing = conn.execute(
            "SELECT task_id, agent_id, result_hash, committed_at FROM idempotent_results WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing:
            return {
                "ok": True,
                "duplicate": True,
                "idempotency_key": idempotency_key,
                "result_hash": str(existing["result_hash"]),
                "committed_at": str(existing["committed_at"]),
            }
        conn.execute(
            "INSERT INTO idempotent_results (idempotency_key, task_id, agent_id, result_hash, committed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (idempotency_key, task_id, agent_id, r_hash, now),
        )
    return {"ok": True, "duplicate": False, "idempotency_key": idempotency_key, "result_hash": r_hash, "committed_at": now}


def compute_amdahl_speedup_matrix(serial_fraction: float = 0.15, counts: tuple[int, ...] = (1, 2, 4, 6)) -> list[dict[str, float]]:
    s = max(0.01, min(serial_fraction, 0.99))
    return [{"agents": n, "speedup": round(1.0 / (s + (1.0 - s) / n), 3)} for n in counts]


class LeaseRequest(BaseModel):
    node_id: str = Field(..., min_length=1, max_length=64)
    lease_key: str = Field(default="master-primary", max_length=64)
    ttl_s: int = Field(default=15, ge=3, le=300)


class IdempotentCommitRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=4, max_length=128)
    task_id: str = Field(..., min_length=1, max_length=64)
    agent_id: str = Field(..., min_length=1, max_length=64)
    payload: str = Field(default="", max_length=32000)


@router.post("/lease")
async def api_acquire_lease(body: LeaseRequest):
    """Acquire or renew the HA leader lease with automatic failover on expiry or drain."""
    return {"ok": True, **acquire_or_renew_lease(body.node_id, body.lease_key, body.ttl_s)}


@router.get("/status")
async def api_ha_status(lease_key: str = "master-primary"):
    """Return active HA leader status and Amdahl 1/2/4/6-agent speedup projections."""
    return {**get_ha_status(lease_key), "speedup_matrix": compute_amdahl_speedup_matrix()}


@router.post("/drain/{node_id}")
async def api_drain_node(node_id: str, lease_key: str = "master-primary"):
    """Mark an active leader node as draining for zero-downtime rolling upgrade."""
    return drain_leader_node(node_id, lease_key)


@router.post("/idempotency/commit")
async def api_idempotent_commit(body: IdempotentCommitRequest):
    """Commit a distributed task result idempotently, preventing duplicate writes under retries."""
    return commit_idempotent_result(body.idempotency_key, body.task_id, body.agent_id, body.payload)
