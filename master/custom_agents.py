"""EPK-11: Versioned Custom Assistant/Agent Registry with RAG Bindings, Tool Scopes & Rollback."""

from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import dbconn
import user_profile

router = APIRouter(prefix="/api/custom-agents", tags=["custom-agents"])


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(dbconn.database_file("platform.db"))


def init_custom_agents_db() -> None:
    with _connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS custom_agents ("
            "agent_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL, "
            "current_version INTEGER NOT NULL DEFAULT 1, instructions TEXT NOT NULL, "
            "rag_collections_json TEXT NOT NULL DEFAULT '[]', allowed_tools_json TEXT NOT NULL DEFAULT '[]', "
            "model_override TEXT NOT NULL DEFAULT '', shared_org_id TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS custom_agent_versions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL, user_id TEXT NOT NULL, "
            "version INTEGER NOT NULL, instructions TEXT NOT NULL, allowed_tools_json TEXT NOT NULL DEFAULT '[]', "
            "created_at TEXT NOT NULL)"
        )


def upsert_custom_agent(body: dict[str, Any]) -> dict[str, Any]:
    init_custom_agents_db()
    uid = user_profile.valid_user_id(str(body.get("user_id") or "default"))
    aid = str(body.get("agent_id") or "").strip() or f"ag_{secrets.token_hex(6)}"
    now = datetime.now(UTC).isoformat()
    tools_j = json.dumps(list(body.get("allowed_tools") or []), ensure_ascii=False)
    rags_j = json.dumps(list(body.get("rag_collections") or []), ensure_ascii=False)
    instructions = str(body.get("instructions") or "").strip()
    name = str(body.get("name") or "Özel Asistan").strip()
    with _connect() as conn:
        existing = conn.execute(
            "SELECT current_version FROM custom_agents WHERE agent_id = ? AND user_id = ?",
            (aid, uid),
        ).fetchone()
        ver = int(existing["current_version"]) + 1 if existing else 1
        conn.execute(
            "INSERT OR REPLACE INTO custom_agents "
            "(agent_id, user_id, name, current_version, instructions, rag_collections_json, allowed_tools_json, model_override, shared_org_id, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (aid, uid, name, ver, instructions, rags_j, tools_j, str(body.get("model_override") or ""), str(body.get("shared_org_id") or ""), now),
        )
        conn.execute(
            "INSERT INTO custom_agent_versions (agent_id, user_id, version, instructions, allowed_tools_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (aid, uid, ver, instructions, tools_j, now),
        )
    return {"ok": True, "agent_id": aid, "user_id": uid, "name": name, "version": ver, "updated_at": now}


def list_custom_agents(user_id: str) -> list[dict[str, Any]]:
    init_custom_agents_db()
    uid = user_profile.valid_user_id(user_id)
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM custom_agents WHERE user_id = ? ORDER BY updated_at DESC",
            (uid,),
        ).fetchall()
    return [
        {**dict(r), "rag_collections": json.loads(r["rag_collections_json"]), "allowed_tools": json.loads(r["allowed_tools_json"])}
        for r in rows
    ]


def rollback_custom_agent(agent_id: str, user_id: str, target_version: int) -> dict[str, Any]:
    init_custom_agents_db()
    uid = user_profile.valid_user_id(user_id)
    with _connect() as conn:
        vrow = conn.execute(
            "SELECT instructions, allowed_tools_json FROM custom_agent_versions "
            "WHERE agent_id = ? AND user_id = ? AND version = ?",
            (agent_id, uid, target_version),
        ).fetchone()
        if not vrow:
            raise KeyError(f"Sürüm bulunamadı: {agent_id} v{target_version}")
        now = datetime.now(UTC).isoformat()
        conn.execute(
            "UPDATE custom_agents SET current_version = ?, instructions = ?, allowed_tools_json = ?, updated_at = ? "
            "WHERE agent_id = ? AND user_id = ?",
            (target_version, vrow["instructions"], vrow["allowed_tools_json"], now, agent_id, uid),
        )
    return {"ok": True, "agent_id": agent_id, "restored_version": target_version, "instructions": vrow["instructions"]}


class CustomAgentRequest(BaseModel):
    agent_id: str | None = Field(default=None, max_length=64)
    user_id: str = Field(default="default", max_length=64)
    name: str = Field(..., min_length=2, max_length=80)
    instructions: str = Field(..., min_length=4, max_length=8000)
    rag_collections: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    model_override: str = Field(default="", max_length=80)
    shared_org_id: str = Field(default="", max_length=64)


class RollbackAgentRequest(BaseModel):
    user_id: str = Field(default="default", max_length=64)
    target_version: int = Field(..., ge=1, le=1000)


@router.get("")
async def api_list_custom_agents(user_id: str = Query(default="default")):
    """List versioned custom assistants belonging to a user."""
    try:
        items = list_custom_agents(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "count": len(items), "agents": items}


@router.post("")
async def api_upsert_custom_agent(body: CustomAgentRequest):
    """Create or publish a new version of a custom assistant."""
    try:
        return upsert_custom_agent(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{agent_id}/rollback")
async def api_rollback_custom_agent(agent_id: str, body: RollbackAgentRequest):
    """Roll back a custom assistant to a previously saved immutable version."""
    try:
        return rollback_custom_agent(agent_id, body.user_id, body.target_version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
