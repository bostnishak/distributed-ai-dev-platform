"""EPK-12: Signed HMAC-SHA256 Webhooks, Delivery Log & 5-Field Cron Expression Validator."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

import dbconn

router = APIRouter(prefix="/api/automation", tags=["automation-webhooks"])

_CRON_FIELD_RE = re.compile(r"^(\*|\d+(-\d+)?(,\d+(-\d+)?)*)(/\d+)?$")
_CRON_BOUNDS: tuple[tuple[str, int, int], ...] = (
    ("minute", 0, 59),
    ("hour", 0, 23),
    ("day_of_month", 1, 31),
    ("month", 1, 12),
    ("day_of_week", 0, 7),
)


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("platform.db"))


def init_webhooks_db() -> None:
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS webhook_deliveries ("
            "delivery_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, target_url TEXT NOT NULL, "
            "signature_hmac TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued', "
            "attempts INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)"
        )


def sign_webhook_payload(payload: str, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_webhook_signature(payload: str, secret: str, signature: str) -> bool:
    expected = sign_webhook_payload(payload, secret)
    return hmac.compare_digest(expected, (signature or "").strip())


def record_signed_webhook(event_type: str, target_url: str, payload: str, secret: str) -> dict[str, Any]:
    init_webhooks_db()
    sig = sign_webhook_payload(payload, secret)
    did = f"wh_{secrets.token_hex(6)}"
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO webhook_deliveries (delivery_id, event_type, target_url, signature_hmac, status, attempts, created_at) "
            "VALUES (?, ?, ?, ?, 'signed', 1, ?)",
            (did, event_type, target_url, sig, now),
        )
    return {"ok": True, "delivery_id": did, "event_type": event_type, "signature": sig, "created_at": now}


def validate_cron_expression(expr: str) -> dict[str, Any]:
    """Validate standard 5-field POSIX cron syntax and numeric field bounds."""
    parts = (expr or "").strip().split()
    if len(parts) != 5:
        return {"ok": True, "valid": False, "error": "Cron ifadesi tam 5 alandan oluşmalıdır (dk saat gün ay haftanın_günü)."}
    for part, (name, lo, hi) in zip(parts, _CRON_BOUNDS, strict=True):
        if not _CRON_FIELD_RE.match(part):
            return {"ok": True, "valid": False, "error": f"Geçersiz cron sözdizimi ({name}): {part}"}
        for num_s in re.findall(r"\d+", part.split("/", 1)[0]):
            val = int(num_s)
            if val < lo or val > hi:
                return {"ok": True, "valid": False, "error": f"{name} değeri sınır dışı ({val} not in {lo}..{hi})."}
    return {"ok": True, "valid": True, "expression": " ".join(parts), "fields": dict(zip((b[0] for b in _CRON_BOUNDS), parts, strict=True))}


class SignWebhookRequest(BaseModel):
    event_type: str = Field(default="task.completed", max_length=64)
    target_url: str = Field(default="http://127.0.0.1:9000/hook", max_length=512)
    payload: str = Field(default="{}", max_length=32000)
    secret: str = Field(..., min_length=4, max_length=256)


class VerifyWebhookRequest(BaseModel):
    payload: str = Field(default="", max_length=32000)
    secret: str = Field(..., min_length=4, max_length=256)
    signature: str = Field(..., min_length=8, max_length=128)


class CronValidateRequest(BaseModel):
    expression: str = Field(..., min_length=5, max_length=64)


@router.post("/webhooks/sign")
async def api_sign_webhook(body: SignWebhookRequest):
    """Sign an outbound webhook payload with HMAC-SHA256 and log the delivery."""
    return record_signed_webhook(body.event_type, body.target_url, body.payload, body.secret)


@router.post("/webhooks/verify")
async def api_verify_webhook(body: VerifyWebhookRequest):
    """Verify an inbound HMAC-SHA256 webhook signature in constant time."""
    return {"ok": True, "verified": verify_webhook_signature(body.payload, body.secret, body.signature)}


@router.post("/cron/validate")
async def api_validate_cron(body: CronValidateRequest):
    """Validate a 5-field POSIX cron schedule expression."""
    return validate_cron_expression(body.expression)
