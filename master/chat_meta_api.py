"""Server-side backup of the sidebar organisation (pins, titles, folders, sections) so it survives a new browser."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import user_profile as up
from kvstore import PersistentDict
from user_api import _enforce_user_access

router = APIRouter(prefix="/api/user", tags=["chat-meta"])
_STORE = PersistentDict("chat_meta")
_MAX_BYTES = 200_000
_KEYS = ("chat_meta", "chat_folders", "chat_sections")


class ChatMetaBody(BaseModel):
    chat_meta: str | None = None
    chat_folders: str | None = None
    chat_sections: str | None = None


def _uid(user_id: str) -> str:
    try:
        return up.valid_user_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{user_id}/chat-meta")
async def get_chat_meta(user_id: str, request: Request) -> dict[str, Any]:
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    return _STORE.get(uid, {})


@router.put("/{user_id}/chat-meta")
async def put_chat_meta(user_id: str, body: ChatMetaBody, request: Request) -> dict[str, bool]:
    uid = _uid(user_id)
    _enforce_user_access(request, uid)
    data = {k: v for k in _KEYS if (v := getattr(body, k)) is not None}
    for value in data.values():
        try:
            json.loads(value)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="Geçersiz JSON.") from exc
    if len(json.dumps(data)) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="Düzen verisi çok büyük.")
    _STORE[uid] = data
    return {"ok": True}
