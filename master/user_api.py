"""REST API for the personal space (profiles, settings, statistics, memory, data export)."""

from __future__ import annotations

import hmac
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel

import config
import memory_engine
import user_profile as up
from access_control import require_local_or_admin
from auth import service as auth_service

router = APIRouter(prefix="/api/user", tags=["user"])


def _has_admin_token(request: Request) -> bool:
    expected = config.ADMIN_TOKEN
    supplied = request.headers.get("x-admin-token", "")
    return bool(expected and hmac.compare_digest(supplied.encode(), expected.encode()))


def _enforce_profiles_admin(request: Request) -> None:
    """ALT-07: Listing all profiles requires an admin session or X-Admin-Token once auth is active."""
    if not auth_service.has_any_user() or _has_admin_token(request):
        return
    user = auth_service.get_session_user(request.cookies.get(auth_service.SESSION_COOKIE_NAME))
    if not user:
        raise HTTPException(status_code=401, detail="Bu işlem için oturum açmanız gerekir.")
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Tüm profilleri listeleme yetkiniz yok.")


def _enforce_user_access(request: Request, target_user_id: str) -> None:
    """ALT-07 & ALT-08: Prevent unauthenticated access and cross-user IDOR on /api/user/{user_id}/*."""
    if not auth_service.has_any_user() or _has_admin_token(request):
        return
    user = auth_service.get_session_user(request.cookies.get(auth_service.SESSION_COOKIE_NAME))
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı verilerine erişmek için oturum açmanız gerekir.")
    if user.get("role") == "admin":
        return
    allowed_ids = {str(user.get("username") or "").lower(), str(user.get("id") or "").lower()}
    if target_user_id.lower() not in allowed_ids:
        raise HTTPException(status_code=403, detail="Başka bir kullanıcının profiline veya verilerine erişemezsiniz.")


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
async def list_profiles(request: Request):
    """List local user profiles (admin-only when auth is enabled; ALT-07)."""
    _enforce_profiles_admin(request)
    return {"profiles": up.list_profiles(), "avatar_colors": list(up.AVATAR_COLORS)}


@router.post("/profiles")
async def create_profile(body: CreateProfileBody, request: Request):
    """Create a new local profile (admin-only when auth is enabled; ALT-07)."""
    _enforce_profiles_admin(request)
    try:
        return up.create_profile(body.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{user_id}/profile")
async def get_profile(user_id: str, request: Request):
    """Return a user's profile and preferences (ALT-08)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    return up.get_profile(uid)


@router.put("/{user_id}/profile")
async def update_profile(user_id: str, body: UpdateProfileBody, request: Request):
    """Update an existing user profile; never auto-creates nonexistent arbitrary IDs (ALT-07)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    existing_ids = {p["user_id"] for p in up.list_profiles()} | {"default"}
    if uid not in existing_ids:
        raise HTTPException(status_code=404, detail="Profil bulunamadı.")
    return up.update_profile(
        uid,
        display_name=body.display_name,
        role_title=body.role_title,
        bio=body.bio,
        avatar_color=body.avatar_color,
        settings=body.settings,
    )


@router.delete("/{user_id}", dependencies=[Depends(require_local_or_admin)])
async def delete_profile(user_id: str, request: Request):
    """Delete a non-default user profile (ALT-07)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    try:
        up.delete_profile(uid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/{user_id}/stats")
async def stats(user_id: str, request: Request, days: int = Query(30, ge=1, le=365)):
    """Return usage statistics for the authenticated user (ALT-08)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    return up.usage_summary(uid, days)


@router.get("/{user_id}/personalization-preview")
async def personalization_preview(user_id: str, request: Request):
    """Preview the hidden personalization system note for the user (ALT-08)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    return {"system_note": up.personalization_block(uid)}


@router.get("/{user_id}/memories")
async def list_memories(user_id: str, request: Request):
    """List learned semantic memories belonging to the user (ALT-08)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    return {"memories": memory_engine.list_semantic_facts(user_id=uid)}


@router.post("/{user_id}/memories")
async def add_memory(user_id: str, body: FactBody, request: Request):
    """Add a semantic memory fact for the user (ALT-08)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    try:
        return up.add_fact(uid, body.category, body.fact_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{user_id}/memories/{fact_id}")
async def delete_memory(user_id: str, fact_id: int, request: Request):
    """Delete a semantic memory fact owned by the user (ALT-08)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    if not up.delete_fact(uid, fact_id):
        raise HTTPException(status_code=404, detail="Bilgi bulunamadi.")
    return {"ok": True}


@router.get("/{user_id}/conversations")
async def conversations(user_id: str, request: Request):
    """List conversation history owned by the user (ALT-08)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    return {"conversations": up.list_conversations(uid)}


@router.get("/{user_id}/chats")
async def get_saved_chats(user_id: str, request: Request):
    """List saved assistant chats owned by the user (ALT-08)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    return {"chats": up.list_saved_chats(uid)}


@router.put("/{user_id}/chats/{chat_id}")
async def put_saved_chat(user_id: str, chat_id: str, body: SavedChatBody, request: Request):
    """Create or update a saved assistant chat for the user (ALT-08)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    try:
        return up.upsert_saved_chat(uid, chat_id, body.title, body.updatedAt, body.messages)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{user_id}/chats/{chat_id}")
async def remove_saved_chat(user_id: str, chat_id: str, request: Request):
    """Delete a saved assistant chat for the user (ALT-08)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    up.delete_saved_chat(uid, chat_id)
    return {"ok": True}


@router.get("/{user_id}/history/search")
async def search_history(user_id: str, request: Request, q: str = Query("", max_length=200)):
    """Search cross-chat snippets owned by the user (ALT-08)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    return {"results": up.cross_chat_snippets(uid, q, limit=12)}


@router.get("/{user_id}/export", dependencies=[Depends(require_local_or_admin)])
async def export_data(user_id: str, request: Request):
    """Export all data owned by the user as JSON (ALT-08)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    payload = json.dumps(up.export_all(uid), ensure_ascii=False, indent=2)
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{uid}-veri-aktarimi.json"'},
    )


@router.delete("/{user_id}/data", dependencies=[Depends(require_local_or_admin)])
async def wipe(user_id: str, request: Request, scope: str = Query("usage")):
    """Wipe user data for the requested scope (ALT-08)."""
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    try:
        return {"ok": True, "removed": up.wipe_data(uid, scope)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
