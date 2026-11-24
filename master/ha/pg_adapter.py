"""Optional PostgreSQL Multi-Master HA Lease Adapter with automatic SQLite WAL fallback."""

from __future__ import annotations

import importlib
import importlib.util
import os
from datetime import UTC, datetime, timedelta
from typing import Any

PG_SCHEMA_SQL = (
    "CREATE TABLE IF NOT EXISTS ha_leases ("
    "lease_key TEXT PRIMARY KEY, leader_id TEXT NOT NULL, expires_at TIMESTAMPTZ NOT NULL, "
    "term INTEGER NOT NULL DEFAULT 1, draining BOOLEAN NOT NULL DEFAULT FALSE, updated_at TIMESTAMPTZ NOT NULL)"
)


def detect_ha_backend() -> dict[str, Any]:
    """Detect whether PostgreSQL HA backend is configured & driver installed, else report SQLite WAL."""
    db_url = os.environ.get("DATABASE_URL", "").strip()
    is_pg = db_url.startswith(("postgresql://", "postgres://"))
    has_psycopg = importlib.util.find_spec("psycopg") is not None
    return {
        "active_backend": "postgresql" if (is_pg and has_psycopg) else "sqlite_wal",
        "postgres_configured": is_pg,
        "psycopg_installed": has_psycopg,
        "multi_master_ready": is_pg and has_psycopg,
    }


class PostgresLeaseAdapter:
    """Atomic PostgreSQL leader lease backend used when DATABASE_URL=postgresql://... and psycopg are available."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def _open(self) -> Any:
        psycopg = importlib.import_module("psycopg")
        return psycopg.connect(self.dsn, autocommit=True)

    def init_schema(self) -> None:
        with self._open() as conn, conn.cursor() as cur:
            cur.execute(PG_SCHEMA_SQL)

    def acquire_or_renew(self, node_id: str, lease_key: str = "master-primary", ttl_s: int = 15) -> dict[str, Any]:
        self.init_schema()
        now = datetime.now(UTC)
        new_exp = now + timedelta(seconds=max(3, min(ttl_s, 300)))
        with self._open() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ha_leases (lease_key, leader_id, expires_at, term, draining, updated_at) "
                "VALUES (%s, %s, %s, 1, FALSE, %s) "
                "ON CONFLICT (lease_key) DO UPDATE SET "
                "leader_id = CASE WHEN ha_leases.leader_id = EXCLUDED.leader_id AND NOT ha_leases.draining THEN EXCLUDED.leader_id "
                "WHEN ha_leases.expires_at <= %s OR ha_leases.draining THEN EXCLUDED.leader_id ELSE ha_leases.leader_id END, "
                "term = CASE WHEN ha_leases.leader_id != EXCLUDED.leader_id AND (ha_leases.expires_at <= %s OR ha_leases.draining) "
                "THEN ha_leases.term + 1 ELSE ha_leases.term END, "
                "expires_at = CASE WHEN ha_leases.leader_id = EXCLUDED.leader_id OR ha_leases.expires_at <= %s OR ha_leases.draining "
                "THEN EXCLUDED.expires_at ELSE ha_leases.expires_at END, "
                "draining = CASE WHEN ha_leases.expires_at <= %s OR ha_leases.draining THEN FALSE ELSE ha_leases.draining END, "
                "updated_at = EXCLUDED.updated_at "
                "RETURNING leader_id, term, expires_at",
                (lease_key, node_id, new_exp, now, now, now, now, now),
            )
            row = cur.fetchone()
        leader = str(row[0]) if row else node_id
        return {
            "acquired": leader == node_id,
            "leader_id": leader,
            "term": int(row[1]) if row else 1,
            "expires_at": row[2].isoformat() if row else new_exp.isoformat(),
            "backend": "postgresql",
        }
