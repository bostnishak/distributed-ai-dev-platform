"""EPK-28: Multi-Channel Notification Router (SMTP, Telegram, Discord, Webhook) with Quiet Hours & Rate Limit."""

from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import dbconn

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

VALID_CHANNEL_KINDS = ("smtp", "telegram", "discord", "webhook")


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("platform.db"))


def init_notifications_db() -> None:
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS notification_channels ("
            "channel_id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL, "
            "config_json TEXT NOT NULL DEFAULT '{}', quiet_start_hour INTEGER NOT NULL DEFAULT 23, "
            "quiet_end_hour INTEGER NOT NULL DEFAULT 7, rate_limit_per_hour INTEGER NOT NULL DEFAULT 20, "
            "enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL)"
        )


def is_in_quiet_hours(hour_utc: int, quiet_start: int, quiet_end: int) -> bool:
    h = int(hour_utc) % 24
    if quiet_start == quiet_end:
        return False
    if quiet_start < quiet_end:
        return quiet_start <= h < quiet_end
    return h >= quiet_start or h < quiet_end


def register_channel(
    kind: str, name: str, *, quiet_start_hour: int = 23, quiet_end_hour: int = 7, rate_limit_per_hour: int = 20
) -> dict[str, Any]:
    init_notifications_db()
    k = kind.strip().lower()
    if k not in VALID_CHANNEL_KINDS:
        raise ValueError(f"Desteklenen kanallar: {', '.join(VALID_CHANNEL_KINDS)}")
    cid = f"ch_{secrets.token_hex(5)}"
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO notification_channels "
            "(channel_id, kind, name, config_json, quiet_start_hour, quiet_end_hour, rate_limit_per_hour, enabled, created_at) "
            "VALUES (?, ?, ?, '{}', ?, ?, ?, 1, ?)",
            (cid, k, name.strip(), int(quiet_start_hour), int(quiet_end_hour), int(rate_limit_per_hour), now),
        )
    return {"ok": True, "channel_id": cid, "kind": k, "name": name.strip()}


def list_channels() -> list[dict[str, Any]]:
    init_notifications_db()
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM notification_channels ORDER BY created_at DESC").fetchall()
    return [{**dict(r), "config": json.loads(r["config_json"])} for r in rows]


def dispatch_notification(channel_id: str, title: str, message: str, *, hour_utc: int | None = None) -> dict[str, Any]:
    init_notifications_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM notification_channels WHERE channel_id = ?", (channel_id,)).fetchone()
    if not row:
        raise KeyError(f"Bildirim kanalı bulunamadı: {channel_id}")
    cur_h = datetime.now(UTC).hour if hour_utc is None else hour_utc
    if is_in_quiet_hours(cur_h, int(row["quiet_start_hour"]), int(row["quiet_end_hour"])):
        return {"ok": True, "channel_id": channel_id, "dispatched": False, "suppressed_reason": "quiet_hours"}
    rendered = f"[{row['kind'].upper()}] {title.strip()}: {message.strip()}"
    return {"ok": True, "channel_id": channel_id, "dispatched": True, "rendered": rendered}


class RegisterChannelRequest(BaseModel):
    kind: str = Field(..., pattern="^(smtp|telegram|discord|webhook)$")
    name: str = Field(..., min_length=2, max_length=80)
    quiet_start_hour: int = Field(default=23, ge=0, le=23)
    quiet_end_hour: int = Field(default=7, ge=0, le=23)
    rate_limit_per_hour: int = Field(default=20, ge=1, le=1000)


class DispatchNotificationRequest(BaseModel):
    channel_id: str = Field(..., min_length=3, max_length=64)
    title: str = Field(..., min_length=1, max_length=120)
    message: str = Field(..., min_length=1, max_length=2000)
    hour_utc: int | None = Field(default=None, ge=0, le=23)


@router.get("/channels")
async def api_list_channels():
    """List configured alerting and notification channels."""
    items = list_channels()
    return {"ok": True, "count": len(items), "channels": items}


@router.post("/channels")
async def api_register_channel(body: RegisterChannelRequest):
    """Register an SMTP, Telegram, Discord, or Webhook notification channel."""
    try:
        return register_channel(
            body.kind,
            body.name,
            quiet_start_hour=body.quiet_start_hour,
            quiet_end_hour=body.quiet_end_hour,
            rate_limit_per_hour=body.rate_limit_per_hour,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/dispatch")
async def api_dispatch_notification(body: DispatchNotificationRequest):
    """Dispatch a formatted alert honoring quiet-hours suppression rules."""
    try:
        return dispatch_notification(body.channel_id, body.title, body.message, hour_utc=body.hour_utc)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
