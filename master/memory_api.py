"""Cluster A (`[M04]` & Faz 1.2): Persistent Cognitive Memory REST API Router.

Exposes:
- `GET /api/memory/conversations`: lists episodic conversations for a user profile
- `GET /api/memory/facts`: lists learned semantic facts for a user profile
- `DELETE /api/memory/facts/{id}`: deletes a semantic fact by ID
- `POST /api/memory/compact/{conversation_id}`: runs hierarchical context compaction on a conversation's messages and updates `conversations.summary`
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query

import memory_engine
import user_profile

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/conversations")
def get_memory_conversations(
    user_id: str = Query(default=user_profile.DEFAULT_USER_ID),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """List conversations from episodic memory for the given user profile."""
    try:
        uid = user_profile.valid_user_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    conversations = user_profile.list_conversations(uid, limit=limit)
    return {
        "ok": True,
        "user_id": uid,
        "count": len(conversations),
        "conversations": conversations,
    }


@router.get("/facts")
def get_memory_facts(
    user_id: str = Query(default=user_profile.DEFAULT_USER_ID),
) -> dict[str, Any]:
    """List learned semantic facts for the given user profile."""
    try:
        uid = user_profile.valid_user_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    facts = memory_engine.list_semantic_facts(user_id=uid)
    return {
        "ok": True,
        "user_id": uid,
        "count": len(facts),
        "facts": facts,
    }


@router.delete("/facts/{fact_id}")
def delete_memory_fact(
    fact_id: int,
    user_id: str = Query(default=user_profile.DEFAULT_USER_ID),
) -> dict[str, Any]:
    """Delete a semantic memory fact by ID."""
    try:
        uid = user_profile.valid_user_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    deleted = user_profile.delete_fact(uid, fact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Fact id={fact_id} not found for user '{uid}'.")
    return {
        "ok": True,
        "user_id": uid,
        "deleted_id": fact_id,
    }


@router.post("/compact/{conversation_id}")
def compact_conversation(
    conversation_id: str,
    max_chars: int = Query(default=12000, ge=64, le=200000),
) -> dict[str, Any]:
    """Compact a conversation's message history and store the summary in `conversations.summary`."""
    cid = (conversation_id or "").strip()
    if not cid:
        raise HTTPException(status_code=400, detail="conversation_id is required.")

    memory_engine.init_memory_db()
    with memory_engine._connect() as conn:
        conv_row = conn.execute(
            "SELECT id, user_id, title, summary FROM conversations WHERE id = ?",
            (cid,),
        ).fetchone()
        if conv_row is None:
            raise HTTPException(status_code=404, detail=f"Conversation '{cid}' not found.")

        msg_rows = conn.execute(
            "SELECT role, content FROM conversation_messages WHERE conversation_id = ? ORDER BY id ASC",
            (cid,),
        ).fetchall()

        raw_messages = [{"role": str(r["role"]), "content": str(r["content"])} for r in msg_rows]
        # Force compaction when explicit compact endpoint is called with short threshold or long history
        effective_max_chars = min(max_chars, max(64, sum(len(m["content"]) for m in raw_messages) // 2))
        compacted = memory_engine.compact_conversation_context(raw_messages, max_chars=effective_max_chars)

        summary_text = ""
        for item in compacted:
            if item.get("role") == "system" and "özeti" in item.get("content", "").lower():
                summary_text = item["content"]
                break

        if not summary_text and raw_messages:
            snippets = [
                f"[{m['role'].upper()}]: {m['content'].strip().replace(chr(10), ' ')[:160]}"
                for m in raw_messages[-12:]
                if m.get("content", "").strip()
            ]
            summary_text = "Önceki konuşma turlarının sıkıştırılmış özeti:\n" + "\n".join(snippets)

        now = datetime.now(UTC).isoformat()
        conn.execute(
            "UPDATE conversations SET summary = ?, updated_at = ? WHERE id = ?",
            (summary_text, now, cid),
        )

    return {
        "ok": True,
        "conversation_id": cid,
        "original_message_count": len(raw_messages),
        "compacted_message_count": len(compacted),
        "summary": summary_text,
        "compacted_messages": compacted,
    }
