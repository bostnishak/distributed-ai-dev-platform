"""REST API for the personal space (profiles, settings, statistics, memory, data export)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

import memory_engine
import user_profile as up

router = APIRouter(prefix="/api/user", tags=["user"])


class CreateProfileBody(BaseModel):
    display_name: str


class UpdateProfileBody(BaseModel):
    display_name: str | None = None
    role_title: str | None = None
    bio: str | None = None
    avatar_color: str | None = None
    settings: dict[str, Any] | None = None


class FactBody(BaseModel):
    category: str = "preference"
    fact_value: str


class SavedChatBody(BaseModel):
    title: str = "Yeni sohbet"
    updatedAt: int = 0
    messages: list[dict[str, Any]] = []


def _uid(user_id: str) -> str:
    try:
        return up.valid_user_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/profiles")
async def list_profiles():
    return {"profiles": up.list_profiles(), "avatar_colors": list(up.AVATAR_COLORS)}


@router.post("/profiles")
async def create_profile(body: CreateProfileBody):
    try:
        return up.create_profile(body.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{user_id}/profile")
async def get_profile(user_id: str):
    return up.get_profile(_uid(user_id))


@router.put("/{user_id}/profile")
async def update_profile(user_id: str, body: UpdateProfileBody):
    return up.update_profile(
        _uid(user_id),
        display_name=body.display_name,
        role_title=body.role_title,
        bio=body.bio,
        avatar_color=body.avatar_color,
        settings=body.settings,
    )


@router.delete("/{user_id}")
async def delete_profile(user_id: str):
    try:
        up.delete_profile(_uid(user_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/{user_id}/stats")
async def stats(user_id: str, days: int = Query(30, ge=1, le=365)):
    return up.usage_summary(_uid(user_id), days)


@router.get("/{user_id}/personalization-preview")
async def personalization_preview(user_id: str):
    return {"system_note": up.personalization_block(_uid(user_id))}


@router.get("/{user_id}/memories")
async def list_memories(user_id: str):
    return {"memories": memory_engine.list_semantic_facts(user_id=_uid(user_id))}


@router.post("/{user_id}/memories")
async def add_memory(user_id: str, body: FactBody):
    try:
        return up.add_fact(_uid(user_id), body.category, body.fact_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{user_id}/memories/{fact_id}")
async def delete_memory(user_id: str, fact_id: int):
    if not up.delete_fact(_uid(user_id), fact_id):
        raise HTTPException(status_code=404, detail="Bilgi bulunamadi.")
    return {"ok": True}


@router.get("/{user_id}/conversations")
async def conversations(user_id: str):
    return {"conversations": up.list_conversations(_uid(user_id))}


@router.get("/{user_id}/chats")
async def get_saved_chats(user_id: str):
    return {"chats": up.list_saved_chats(_uid(user_id))}


@router.put("/{user_id}/chats/{chat_id}")
async def put_saved_chat(user_id: str, chat_id: str, body: SavedChatBody):
    try:
        return up.upsert_saved_chat(_uid(user_id), chat_id, body.title, body.updatedAt, body.messages)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{user_id}/chats/{chat_id}")
async def remove_saved_chat(user_id: str, chat_id: str):
    up.delete_saved_chat(_uid(user_id), chat_id)
    return {"ok": True}


@router.get("/{user_id}/history/search")
async def search_history(user_id: str, q: str = Query("", max_length=200)):
    return {"results": up.cross_chat_snippets(_uid(user_id), q, limit=12)}


@router.get("/{user_id}/export")
async def export_data(user_id: str):
    uid = _uid(user_id)
    payload = json.dumps(up.export_all(uid), ensure_ascii=False, indent=2)
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{uid}-veri-aktarimi.json"'},
    )


@router.delete("/{user_id}/data")
async def wipe(user_id: str, scope: str = Query("usage")):
    try:
        return {"ok": True, "removed": up.wipe_data(_uid(user_id), scope)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
