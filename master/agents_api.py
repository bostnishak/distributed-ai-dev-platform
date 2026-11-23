"""Agent registry API with per-agent identity keys, revocation, rotation, and optional admin approval (SEC-18)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

import config
import db
from access_control import require_local_or_admin
from audit_log import AuditTrail

router = APIRouter(prefix="/api/agents", tags=["agents"])

ONLINE_THRESHOLD_SECONDS = 300  # 5 minutes — covers demo restarts


class RegisterRequest(BaseModel):
    agent_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,31}$")
    member_name: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=100)
    mode: Literal["node", "staging"] = "node"
    runtime: Literal["native", "docker"] | None = None
    hostname: str | None = Field(default=None, max_length=255)
    os: str | None = Field(default=None, max_length=120)
    cpu_count: int | None = Field(default=None, ge=1, le=4096)
    ram_gb: float | None = Field(default=None, ge=0, le=65536)
    model_family: str | None = Field(default=None, max_length=60)
    parameter_size: str | None = Field(default=None, max_length=30)
    quantization: str | None = Field(default=None, max_length=30)
    context_length: int | None = Field(default=None, ge=1)
    capabilities: list[str] = Field(default_factory=list, max_length=20)
    agent_version: str | None = Field(default=None, max_length=30)


class HeartbeatRequest(BaseModel):
    status: Literal["idle", "busy"] = "idle"
    loaded_models: list[str] = Field(default_factory=list, max_length=20)
    vram_used_gb: float | None = Field(default=None, ge=0, le=1024)
    tokens_per_sec: float | None = Field(default=None, ge=0, le=10000)


LIVE_AGENT_TELEMETRY: dict[str, dict] = {}


def _hash_agent_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _generate_agent_key() -> str:
    return f"agt_{secrets.token_hex(24)}"


def _lookup_agent_by_key(raw_key: str) -> dict | None:
    kh = _hash_agent_key(raw_key)
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM agents WHERE agent_key_hash = ?", (kh,)).fetchone()
    return dict(row) if row else None


def _is_agent_revoked(agent_id: str) -> bool:
    with db.connect() as conn:
        row = conn.execute("SELECT agent_key_revoked, approved FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
    if not row:
        return False
    return bool(row["agent_key_revoked"]) or not bool(row["approved"])


def require_agent_token(authorization: str | None = Header(default=None)) -> None:
    """Verify bootstrap registration token (`AGENT_TOKEN`)."""
    if not config.AGENT_TOKEN:
        raise HTTPException(status_code=503, detail="Master'da AGENT_TOKEN ayarlanmamış.")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme != "Bearer" or not secrets.compare_digest(token.encode(), config.AGENT_TOKEN.encode()):
        raise HTTPException(status_code=401, detail="Geçersiz ajan anahtarı (AGENT_TOKEN).")


def require_agent_auth(
    request: Request,
    authorization: str | None = Header(default=None),
    x_agent_key: str | None = Header(default=None),
    x_agent_id: str | None = Header(default=None),
) -> str | None:
    """SEC-18: Authenticate an agent via its unique per-agent key (`agt_...`) or shared `AGENT_TOKEN`.

    Returns the authenticated `agent_id` when per-agent key or `X-Agent-Id` is supplied so callers
    can strictly enforce task ownership (`403` when Agent A tries to act on Agent B's task).
    """
    scheme, _, bearer_tok = (authorization or "").partition(" ")
    candidate_key = (x_agent_key or "").strip()
    if not candidate_key and scheme == "Bearer" and bearer_tok.startswith("agt_"):
        candidate_key = bearer_tok.strip()

    # 1. Per-agent key path (SEC-18 preferred)
    if candidate_key:
        agent_row = _lookup_agent_by_key(candidate_key)
        if not agent_row:
            raise HTTPException(status_code=401, detail="Geçersiz ajan anahtarı.")
        if agent_row.get("agent_key_revoked"):
            AuditTrail().append_event(
                actor=str(agent_row["agent_id"]),
                action="AGENT_REVOKED_KEY_REJECTED",
                payload={"path": str(request.url.path)},
            )
            raise HTTPException(status_code=401, detail="Bu ajan anahtarı iptal edilmiş.")
        if not agent_row.get("approved", 1):
            raise HTTPException(status_code=403, detail="Bu ajan henüz yönetici tarafından onaylanmamış.")
        return str(agent_row["agent_id"])

    # 2. Legacy shared AGENT_TOKEN fallback (still checks revocation if X-Agent-Id is provided)
    if not config.AGENT_TOKEN:
        raise HTTPException(status_code=503, detail="Master'da AGENT_TOKEN ayarlanmamış.")
    if scheme != "Bearer" or not secrets.compare_digest(bearer_tok.encode(), config.AGENT_TOKEN.encode()):
        raise HTTPException(status_code=401, detail="Geçersiz ajan anahtarı (AGENT_TOKEN).")
    if x_agent_id:
        aid = x_agent_id.strip()
        if _is_agent_revoked(aid):
            raise HTTPException(status_code=401, detail="Bu ajan anahtarı iptal edilmiş veya onaysız.")
        return aid
    return None


def _compute_online(agent: dict) -> bool:
    last_seen = agent.get("last_seen_at")
    if not last_seen:
        return False
    try:
        ts = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return (datetime.now(UTC) - ts).total_seconds() < ONLINE_THRESHOLD_SECONDS
    except (ValueError, TypeError):
        return False


def _with_online(agent: dict) -> dict:
    clean = {k: v for k, v in agent.items() if k != "agent_key_hash"}
    tele = LIVE_AGENT_TELEMETRY.get(clean.get("agent_id", ""), {})
    return {**clean, "online": _compute_online(clean), **tele}


@router.post("/register", dependencies=[Depends(require_agent_token)])
def register(request: RegisterRequest):
    # Refuse re-registration if this agent_id was explicitly revoked
    with db.connect() as conn:
        existing = conn.execute(
            "SELECT agent_key_hash, agent_key_revoked, approved FROM agents WHERE agent_id = ?",
            (request.agent_id,),
        ).fetchone()
    if existing and existing["agent_key_revoked"]:
        AuditTrail().append_event(
            actor=request.agent_id,
            action="AGENT_REGISTER_REVOKED_REJECTED",
            payload={"agent_id": request.agent_id},
        )
        raise HTTPException(status_code=401, detail="Bu ajan anahtarı iptal edilmiş; yeniden kayıt yapılamaz.")

    saved = db.upsert_agent(request.model_dump())

    issued_key: str | None = None
    with db.connect() as conn:
        row = conn.execute("SELECT agent_key_hash FROM agents WHERE agent_id = ?", (request.agent_id,)).fetchone()
        if not row or not row["agent_key_hash"]:
            issued_key = _generate_agent_key()
            approved_val = 0 if config.REQUIRE_AGENT_APPROVAL else 1
            conn.execute(
                "UPDATE agents SET agent_key_hash = ?, agent_key_revoked = 0, approved = ? WHERE agent_id = ?",
                (_hash_agent_key(issued_key), approved_val, request.agent_id),
            )
    AuditTrail().append_event(
        actor=request.agent_id,
        action="AGENT_REGISTERED",
        payload={"agent_id": request.agent_id, "model": request.model, "mode": request.mode},
    )
    out = _with_online(saved)
    if issued_key:
        out["agent_key"] = issued_key
    return out


@router.post("/{agent_id}/heartbeat")
def heartbeat(
    agent_id: str,
    request: HeartbeatRequest,
    caller_agent_id: str | None = Depends(require_agent_auth),
):
    if caller_agent_id and caller_agent_id != agent_id:
        raise HTTPException(status_code=403, detail="Başka bir ajan adına yoklama gönderilemez.")
    if _is_agent_revoked(agent_id):
        raise HTTPException(status_code=401, detail="Bu ajan anahtarı iptal edilmiş.")
    found = db.update_heartbeat(agent_id, request.status)
    if not found:
        raise HTTPException(status_code=404, detail="Ajan bulunamadı.")
    LIVE_AGENT_TELEMETRY[agent_id] = {
        "loaded_models": request.loaded_models,
        "vram_used_gb": request.vram_used_gb,
        "tokens_per_sec": request.tokens_per_sec,
    }
    return {"ok": True}


@router.post("/{agent_id}/revoke-key", dependencies=[Depends(require_local_or_admin)])
def revoke_agent_key(agent_id: str):
    """SEC-18: Revoke an agent's key so it can no longer register, poll, or submit results."""
    if not db.get_agent(agent_id):
        raise HTTPException(status_code=404, detail="Ajan bulunamadı.")
    with db.connect() as conn:
        conn.execute("UPDATE agents SET agent_key_revoked = 1 WHERE agent_id = ?", (agent_id,))
    AuditTrail().append_event(actor="admin", action="AGENT_KEY_REVOKED", payload={"agent_id": agent_id})
    return {"ok": True, "agent_id": agent_id, "revoked": True}


@router.post("/{agent_id}/rotate-key", dependencies=[Depends(require_local_or_admin)])
def rotate_agent_key(agent_id: str):
    """SEC-18: Issue a fresh per-agent key and clear revocation."""
    if not db.get_agent(agent_id):
        raise HTTPException(status_code=404, detail="Ajan bulunamadı.")
    new_key = _generate_agent_key()
    with db.connect() as conn:
        conn.execute(
            "UPDATE agents SET agent_key_hash = ?, agent_key_revoked = 0, approved = 1 WHERE agent_id = ?",
            (_hash_agent_key(new_key), agent_id),
        )
    AuditTrail().append_event(actor="admin", action="AGENT_KEY_ROTATED", payload={"agent_id": agent_id})
    return {"ok": True, "agent_id": agent_id, "agent_key": new_key}


@router.post("/{agent_id}/approve", dependencies=[Depends(require_local_or_admin)])
def approve_agent(agent_id: str):
    """SEC-18: Admin approval for newly registered agents when REQUIRE_AGENT_APPROVAL is enabled."""
    if not db.get_agent(agent_id):
        raise HTTPException(status_code=404, detail="Ajan bulunamadı.")
    with db.connect() as conn:
        conn.execute("UPDATE agents SET approved = 1, agent_key_revoked = 0 WHERE agent_id = ?", (agent_id,))
    AuditTrail().append_event(actor="admin", action="AGENT_APPROVED", payload={"agent_id": agent_id})
    return {"ok": True, "agent_id": agent_id, "approved": True}


@router.get("/{agent_id}/scores")
def get_scores(agent_id: str):
    if not db.get_agent(agent_id):
        raise HTTPException(status_code=404, detail="Ajan bulunamadı.")
    return db.get_agent_scores(agent_id)


@router.get("")
def list_agents():
    return [_with_online(a) for a in db.list_agents()]
