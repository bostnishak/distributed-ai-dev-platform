"""Agent registry API. Agents register themselves; the master never connects to them (pull model)."""

import secrets
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

import config
import db

router = APIRouter(prefix="/api/agents", tags=["agents"])

ONLINE_THRESHOLD_SECONDS = 30


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


def require_agent_token(authorization: str | None = Header(default=None)) -> None:
    if not config.AGENT_TOKEN:
        raise HTTPException(status_code=503, detail="Master'da AGENT_TOKEN ayarlanmamış.")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme != "Bearer" or not secrets.compare_digest(token.encode(), config.AGENT_TOKEN.encode()):
        raise HTTPException(status_code=401, detail="Geçersiz ajan anahtarı (AGENT_TOKEN).")


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
    return {**agent, "online": _compute_online(agent)}


@router.post("/register", dependencies=[Depends(require_agent_token)])
def register(request: RegisterRequest):
    return _with_online(db.upsert_agent(request.model_dump()))


@router.post("/{agent_id}/heartbeat", dependencies=[Depends(require_agent_token)])
def heartbeat(agent_id: str, request: HeartbeatRequest):
    found = db.update_heartbeat(agent_id, request.status)
    if not found:
        raise HTTPException(status_code=404, detail="Ajan bulunamadı.")
    return {"ok": True}


@router.get("/{agent_id}/scores")
def get_scores(agent_id: str):
    if not db.get_agent(agent_id):
        raise HTTPException(status_code=404, detail="Ajan bulunamadı.")
    return db.get_agent_scores(agent_id)


@router.get("")
def list_agents():
    return [_with_online(a) for a in db.list_agents()]
