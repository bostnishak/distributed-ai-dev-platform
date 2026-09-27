"""Agent registry API. Agents register themselves; the master never connects to them (pull model)."""

import secrets
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

import config
import db

router = APIRouter(prefix="/api/agents", tags=["agents"])


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


def require_agent_token(authorization: str | None = Header(default=None)) -> None:
    if not config.AGENT_TOKEN:
        raise HTTPException(status_code=503, detail="Master'da AGENT_TOKEN ayarlanmamış.")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme != "Bearer" or not secrets.compare_digest(token.encode(), config.AGENT_TOKEN.encode()):
        raise HTTPException(status_code=401, detail="Geçersiz ajan anahtarı (AGENT_TOKEN).")


@router.post("/register", dependencies=[Depends(require_agent_token)])
def register(request: RegisterRequest):
    return db.upsert_agent(request.model_dump())


@router.get("")
def list_agents():
    return db.list_agents()
