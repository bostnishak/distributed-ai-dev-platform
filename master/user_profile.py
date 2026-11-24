"""Personal space: user profiles, UI/assistant settings, token usage statistics and cross-chat memory.

100% local SQLite storage in ``config.DATA_DIR / "user_profile.db"``. Several profiles can exist on
one master (the web UI has no login yet); each profile has its own settings, usage history and
learned memories (the latter live in ``memory_engine``'s ``semantic_memories`` keyed by user_id).
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import dbconn
import dbindexes
import memory_engine
from prompt_loader import load_prompt
from user_profile_helpers import (
    compact_sqlite_physical as _compact_sqlite_physical,
)
from user_profile_helpers import (
    compute_usage_buckets,
    format_selected_chats_lines,
    has_cross_chat_cue,
    is_trivial_query,
    sanitize_bounded_int,
    search_fts_snippets,
    search_saved_chats_snippets,
    select_relevant_chats,
)
from user_profile_helpers import (
    extract_media_filenames as _extract_media_filenames,
)
from user_profile_helpers import (
    fold_tr as _fold_tr,
)
from user_profile_helpers import (
    token_root_match as _token_root_match,
)
from user_profile_helpers import (
    tr_tokens as _tr_tokens,
)

DEFAULT_USER_ID = "default"
_UID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")

DEFAULT_SETTINGS: dict[str, Any] = {
    "theme": "system",
    "accent": "indigo",
    "font_size": "medium",
    "density": "comfortable",
    "reduce_motion": False,
    "send_with_enter": True,
    "show_token_counter": True,
    "show_model_badge": True,
    "response_style": "balanced",
    "tone": "professional",
    "expertise_level": "intermediate",
    "interests": "",
    "custom_instructions": "",
    "cross_chat_memory": True,
    "auto_learn_facts": True,
    "monthly_token_budget": 0,
    "retention_days": 0,
}

_ENUMS: dict[str, set[str]] = {
    "theme": {"system", "light", "dark"},
    "accent": {"indigo", "teal", "emerald", "rose", "amber", "slate"},
    "font_size": {"small", "medium", "large"},
    "density": {"comfortable", "compact"},
    "response_style": {"concise", "balanced", "detailed"},
    "tone": {"professional", "friendly", "technical"},
    "expertise_level": {"beginner", "intermediate", "expert"},
}
_BOOLS = {"reduce_motion", "send_with_enter", "show_token_counter", "show_model_badge", "cross_chat_memory", "auto_learn_facts"}
_TEXT_LIMITS = {"interests": 400, "custom_instructions": 1500}
_INT_BOUNDS = {"monthly_token_budget": 1_000_000_000, "retention_days": 3650}

AVATAR_COLORS = ("#4f46e5", "#0d9488", "#059669", "#e11d48", "#d97706", "#475569")

_STYLE_TEXT = {
    "concise": "Yanitlari kisa ve oz tut; gereksiz giris yapma.",
    "balanced": "Yanitlari dengeli uzunlukta ver; gerektiginde ornek ekle.",
    "detailed": "Yanitlari ayrintili, adim adim ve gerekceleriyle ver.",
}
_TONE_TEXT = {
    "professional": "Resmi ve profesyonel bir dil kullan.",
    "friendly": "Samimi ve sicak bir dil kullan.",
    "technical": "Teknik terimleri cekinmeden kullan, kesin ve olculebilir ifadeler tercih et.",
}
_LEVEL_TEXT = {
    "beginner": "Kullanici yeni baslayan seviyesinde; terimleri acikla.",
    "intermediate": "Kullanici orta seviyede; temel kavramlari tekrar anlatma.",
    "expert": "Kullanici uzman seviyesinde; temel aciklamalari atla, dogrudan ayrintiya gir.",
}


def _db_path() -> Path:
    p = dbconn.database_file("user_profile.db")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _connect() -> sqlite3.Connection:
    return dbconn.open_db(_db_path())


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(load_prompt("b1_user_profile_schema.txt"))
    with _connect() as conn:
        dbindexes.ensure_indexes(conn)


def valid_user_id(user_id: str) -> str:
    uid = (user_id or DEFAULT_USER_ID).strip().lower()
    if not _UID_RE.match(uid):
        raise ValueError("Gecersiz profil kimligi.")
    return uid


def _sanitize_setting_value(key: str, value: Any) -> tuple[bool, Any]:
    if key in _ENUMS:
        return (isinstance(value, str) and value in _ENUMS[key]), value
    if key in _BOOLS:
        return isinstance(value, bool), value
    if key in _TEXT_LIMITS:
        return isinstance(value, str), (value.strip()[: _TEXT_LIMITS[key]] if isinstance(value, str) else None)
    if key in _INT_BOUNDS:
        parsed = sanitize_bounded_int(value, _INT_BOUNDS[key])
        return (parsed is not None), parsed
    return False, None


def sanitize_settings(patch: dict[str, Any]) -> dict[str, Any]:
    """Keep only known keys with valid values; unknown or invalid entries are dropped."""
    clean: dict[str, Any] = {}
    for key, value in (patch or {}).items():
        ok, cleaned = _sanitize_setting_value(key, value)
        if ok:
            clean[key] = cleaned
    return clean


def _row_to_profile(row: sqlite3.Row) -> dict[str, Any]:
    try:
        stored = json.loads(row["settings_json"] or "{}")
    except json.JSONDecodeError:
        stored = {}
    settings = {**DEFAULT_SETTINGS, **sanitize_settings(stored)}
    return {
        "user_id": row["user_id"],
        "display_name": row["display_name"],
        "role_title": row["role_title"],
        "bio": row["bio"],
        "avatar_color": row["avatar_color"],
        "settings": settings,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_profile(user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    """Return the profile, creating it with defaults on first access."""
    init_db()
    uid = valid_user_id(user_id)
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (uid,)).fetchone()
        if row is None:
            name = "Kullanici" if uid == DEFAULT_USER_ID else uid
            conn.execute(
                "INSERT INTO profiles (user_id, display_name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (uid, name, now, now),
            )
            row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (uid,)).fetchone()
    return _row_to_profile(row)


def get_settings(user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    return get_profile(user_id)["settings"]


def list_profiles() -> list[dict[str, Any]]:
    get_profile(DEFAULT_USER_ID)
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM profiles ORDER BY created_at").fetchall()
    return [
        {k: p[k] for k in ("user_id", "display_name", "role_title", "avatar_color")}
        for p in (_row_to_profile(r) for r in rows)
    ]


def create_profile(display_name: str) -> dict[str, Any]:
    name = (display_name or "").strip()[:40]
    if not name:
        raise ValueError("Profil adi bos olamaz.")
    base = re.sub(r"[^a-z0-9]+", "-", name.lower().replace("ı", "i").replace("ğ", "g").replace("ü", "u")
                  .replace("ş", "s").replace("ö", "o").replace("ç", "c")).strip("-") or "profil"
    base = base[:32]
    init_db()
    uid = base
    n = 2
    with _connect() as conn:
        while conn.execute("SELECT 1 FROM profiles WHERE user_id = ?", (uid,)).fetchone():
            uid = f"{base}-{n}"
            n += 1
        now = datetime.now(UTC).isoformat()
        color = AVATAR_COLORS[(n + len(base)) % len(AVATAR_COLORS)]
        conn.execute(
            "INSERT INTO profiles (user_id, display_name, avatar_color, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (uid, name, color, now, now),
        )
    return get_profile(uid)


_PROFILE_UPDATE_FIELDS = ("display_name", "role_title", "bio", "avatar_color", "settings")


def update_profile(user_id: str, *args: Any, **opts: Any) -> dict[str, Any]:
    params = dict(zip(_PROFILE_UPDATE_FIELDS, args, strict=False))
    params.update(opts)
    display_name: str | None = params.get("display_name")
    role_title: str | None = params.get("role_title")
    bio: str | None = params.get("bio")
    avatar_color: str | None = params.get("avatar_color")
    settings: dict[str, Any] | None = params.get("settings")

    current = get_profile(user_id)
    uid = current["user_id"]
    merged = {**current["settings"], **sanitize_settings(settings or {})}
    name = (display_name if display_name is not None else current["display_name"]).strip()[:40] or current["display_name"]
    color = avatar_color if avatar_color in AVATAR_COLORS else current["avatar_color"]
    with _connect() as conn:
        conn.execute(
            """
            UPDATE profiles SET display_name = ?, role_title = ?, bio = ?, avatar_color = ?,
                   settings_json = ?, updated_at = ? WHERE user_id = ?
            """,
            (
                name,
                (role_title if role_title is not None else current["role_title"]).strip()[:60],
                (bio if bio is not None else current["bio"]).strip()[:400],
                color,
                json.dumps(merged, ensure_ascii=False),
                datetime.now(UTC).isoformat(),
                uid,
            ),
        )
    return get_profile(uid)


def delete_profile(user_id: str) -> None:
    uid = valid_user_id(user_id)
    if uid == DEFAULT_USER_ID:
        raise ValueError("Varsayilan profil silinemez.")
    wipe_data(uid, "all")
    with _connect() as conn:
        conn.execute("DELETE FROM profiles WHERE user_id = ?", (uid,))


# ---------------------------------------------------------------- usage tracking

def estimate_tokens(text: str) -> int:
    """Rough token estimate (about 3.5 characters per token) used when the model reports none."""
    return max(0, round(len(text or "") / 3.5))


_USAGE_FIELDS = ("model", "task_type", "prompt_tokens", "completion_tokens", "latency_ms", "estimated")


def record_usage(user_id: str, conversation_id: str, *args: Any, **opts: Any) -> None:
    params = dict(zip(_USAGE_FIELDS, args, strict=False))
    params.update(opts)
    init_db()
    uid = valid_user_id(user_id)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO usage_events
                (user_id, ts, conversation_id, model, task_type, prompt_tokens, completion_tokens, latency_ms, estimated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uid,
                datetime.now(UTC).isoformat(),
                conversation_id or "",
                str(params.get("model") or ""),
                str(params.get("task_type") or ""),
                max(0, int(params.get("prompt_tokens") or 0)),
                max(0, int(params.get("completion_tokens") or 0)),
                max(0, int(params.get("latency_ms") or 0)),
                1 if params.get("estimated") else 0,
            ),
        )


def _month_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def usage_summary(user_id: str, days: int = 30) -> dict[str, Any]:
    init_db()
    uid = valid_user_id(user_id)
    days = max(1, min(int(days), 365))
    today = datetime.now(UTC).date()
    start = today - timedelta(days=days - 1)
    cutoff = datetime(start.year, start.month, start.day, tzinfo=UTC).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM usage_events WHERE user_id = ? AND ts >= ? ORDER BY ts", (uid, cutoff)
        ).fetchall()
        all_days = conn.execute(
            "SELECT DISTINCT substr(ts, 1, 10) AS d FROM usage_events WHERE user_id = ?", (uid,)
        ).fetchall()
        month_tokens = conn.execute(
            "SELECT COALESCE(SUM(prompt_tokens + completion_tokens), 0) AS t FROM usage_events WHERE user_id = ? AND ts >= ?",
            (uid, _month_start().isoformat()),
        ).fetchone()["t"]

    agg = compute_usage_buckets(rows, start, days, all_days, today)
    messages = len(rows)
    prompt_total = int(agg["prompt_total"])
    completion_total = int(agg["completion_total"])
    total_tokens = prompt_total + completion_total
    budget = int(get_settings(uid).get("monthly_token_budget") or 0)
    return {
        "user_id": uid,
        "days": days,
        "totals": {
            "messages": messages,
            "conversations": len(agg["conversations"]),
            "prompt_tokens": prompt_total,
            "completion_tokens": completion_total,
            "total_tokens": total_tokens,
            "avg_tokens_per_message": round(total_tokens / messages) if messages else 0,
            "avg_latency_ms": round(int(agg["latency_total"]) / messages) if messages else 0,
            "streak_days": agg["streak"],
            "active_days": agg["active_days"],
        },
        "daily": [{"date": d, **v} for d, v in agg["daily"].items()],
        "by_model": sorted(({"model": k, **v} for k, v in agg["by_model"].items()), key=lambda x: x["tokens"], reverse=True),
        "by_task": sorted(({"task_type": k, **v} for k, v in agg["by_task"].items()), key=lambda x: x["messages"], reverse=True),
        "by_hour": agg["by_hour"],
        "budget": {
            "monthly_token_budget": budget,
            "month_tokens": int(month_tokens),
            "percent": round(month_tokens / budget * 100, 1) if budget else 0.0,
        },
        "cloud_equivalent_usd": round(prompt_total / 1_000_000 * 1.0 + completion_total / 1_000_000 * 4.0, 4),
    }


# ---------------------------------------------------------------- personalization and memory

def personalization_block(user_id: str) -> str:
    """System-prompt text built from the profile's assistant preferences."""
    profile = get_profile(user_id)
    s = profile["settings"]
    lines = [
        "--- Kullanici Kisisellestirmesi ---",
        f"Kullanicinin adi: {profile['display_name']}"
        + (f" ({profile['role_title']})" if profile["role_title"] else ""),
        _STYLE_TEXT[s["response_style"]],
        _TONE_TEXT[s["tone"]],
        _LEVEL_TEXT[s["expertise_level"]],
    ]
    if s["interests"]:
        lines.append(f"Ilgi alanlari: {s['interests']}")
    if s["custom_instructions"]:
        lines.append(f"Kullanicinin ozel talimatlari: {s['custom_instructions']}")
    return "\n".join(lines)


def cross_chat_snippets(
    user_id: str, query: str, exclude_conversation: str = "", limit: int = 3
) -> list[dict[str, str]]:
    """Search across BOTH saved UI chats and FTS5 episodic conversation messages."""
    memory_engine.init_memory_db()
    uid = valid_user_id(user_id)
    cap = max(1, min(limit, 20))
    raw_q = (query or "").strip()
    if not raw_q:
        return []
    results, seen = search_saved_chats_snippets(list_saved_chats(uid), raw_q, exclude_conversation, cap)
    if len(results) >= cap:
        return results
    fts_hits = search_fts_snippets(uid, raw_q, exclude_conversation, cap - len(results), seen)
    results.extend(fts_hits)
    return results[:cap]


def cross_chat_context_block(user_id: str, query: str, exclude_conversation: str = "") -> str:
    """Provide a directory of saved chats and inject full transcripts of referenced/matched chats."""
    q_folded = _fold_tr(query or "").strip(" ?!.,")
    if is_trivial_query(q_folded):
        return ""
    uid = valid_user_id(user_id)
    saved = list_saved_chats(uid)
    other_chats = [
        (cid, rec)
        for cid, rec in saved.items()
        if cid != (exclude_conversation or "") and (rec.get("messages") or [])
    ]
    lines: list[str] = []
    if other_chats:
        lines.append("--- Kullanicinin Kayitli Diger Sohbetleri ---")
        for _cid, rec in other_chats[:15]:
            title = (rec.get("title") or "Sohbet").strip()
            lines.append(f"- \"{title}\" ({len(rec.get('messages') or [])} mesaj)")
        explicit_ref, generic_recent = has_cross_chat_cue(q_folded)
        selected = select_relevant_chats(other_chats, q_folded, _tr_tokens(query or ""), explicit_ref, generic_recent)
        lines.extend(format_selected_chats_lines(selected))

    hits = cross_chat_snippets(uid, query, exclude_conversation, limit=3)
    if hits:
        lines.append("\n--- FTS5 Sohbet Arasi Ek Eslesmeler ---")
        for h in hits:
            lines.append(f"- ({h['title']}) {h['role']}: {h['snippet']}")
    return "\n".join(lines)


def list_conversations(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    memory_engine.init_memory_db()
    uid = valid_user_id(user_id)
    conn = memory_engine._connect()
    try:
        rows = conn.execute(
            """
            SELECT c.id, c.title, c.updated_at, COUNT(m.id) AS message_count
            FROM conversations c LEFT JOIN conversation_messages m ON m.conversation_id = c.id
            WHERE c.user_id = ? GROUP BY c.id ORDER BY c.updated_at DESC LIMIT ?
            """,
            (uid, max(1, min(limit, 200))),
        ).fetchall()
    finally:
        conn.close()
    by_id: dict[str, dict[str, Any]] = {r["id"]: dict(r) for r in rows}
    for cid, rec in list_saved_chats(uid).items():
        ts_ms = int(rec.get("updatedAt") or 0)
        iso_ts = datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC).isoformat() if ts_ms else datetime.now(UTC).isoformat()
        msgs = rec.get("messages") or []
        if cid not in by_id or len(msgs) > int(by_id[cid].get("message_count") or 0):
            by_id[cid] = {
                "id": cid,
                "title": rec.get("title") or "Sohbet",
                "updated_at": iso_ts,
                "message_count": len(msgs),
            }
    merged = sorted(by_id.values(), key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    return merged[: max(1, min(limit, 200))]


def list_saved_chats(user_id: str) -> dict[str, dict[str, Any]]:
    """Return all full UI chat threads persisted on disk for this profile."""
    init_db()
    uid = valid_user_id(user_id)
    with _connect() as conn:
        rows = conn.execute(
            "SELECT chat_id, title, updated_at, messages_json FROM saved_chats WHERE user_id = ? ORDER BY updated_at DESC",
            (uid,),
        ).fetchall()
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        try:
            msgs = json.loads(r["messages_json"] or "[]")
        except json.JSONDecodeError:
            msgs = []
        out[r["chat_id"]] = {
            "title": r["title"],
            "updatedAt": int(r["updated_at"]),
            "messages": msgs if isinstance(msgs, list) else [],
        }
    return out


def upsert_saved_chat(
    user_id: str,
    chat_id: str,
    title: str,
    updated_at: int,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Persist a full UI chat thread (including inline workspaces and model badges) to disk SQLite."""
    init_db()
    uid = valid_user_id(user_id)
    cid = (chat_id or "").strip()[:80]
    if not cid:
        raise ValueError("Gecersiz sohbet kimligi.")
    clean_title = (title or "Yeni sohbet").strip()[:80] or "Yeni sohbet"
    ts = int(updated_at or int(datetime.now(UTC).timestamp() * 1000))
    payload = json.dumps(messages or [], ensure_ascii=False)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO saved_chats (chat_id, user_id, title, updated_at, messages_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                title = excluded.title,
                updated_at = excluded.updated_at,
                messages_json = excluded.messages_json
            """,
            (cid, uid, clean_title, ts, payload),
        )
    return {"chat_id": cid, "title": clean_title, "updatedAt": ts}


def delete_saved_chat(user_id: str, chat_id: str) -> bool:
    init_db()
    uid = valid_user_id(user_id)
    cid = (chat_id or "").strip()[:80]
    with _connect() as conn:
        cur = conn.execute("DELETE FROM saved_chats WHERE user_id = ? AND chat_id = ?", (uid, cid))
    return cur.rowcount > 0


def delete_fact(user_id: str, fact_id: int) -> bool:
    memory_engine.init_memory_db()
    uid = valid_user_id(user_id)
    conn = memory_engine._connect()
    try:
        with conn:
            cur = conn.execute("DELETE FROM semantic_memories WHERE id = ? AND user_id = ?", (int(fact_id), uid))
        return cur.rowcount > 0
    finally:
        conn.close()


def add_fact(user_id: str, category: str, fact_value: str) -> dict[str, Any]:
    value = (fact_value or "").strip()[:300]
    if not value:
        raise ValueError("Bilgi bos olamaz.")
    cat = (category or "preference").strip()[:40] or "preference"
    return memory_engine.upsert_semantic_fact(cat, f"manual:{value[:24].lower()}", value, user_id=valid_user_id(user_id))


def export_all(user_id: str) -> dict[str, Any]:
    from user_profile_helpers import export_conversations_with_messages

    uid = valid_user_id(user_id)
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "profile": get_profile(uid),
        "memories": memory_engine.list_semantic_facts(user_id=uid),
        "usage": usage_summary(uid, days=365),
        "conversations": export_conversations_with_messages(list_conversations(uid, limit=200)),
        "saved_chats": list_saved_chats(uid),
    }


def purge_expired_data(user_id: str) -> dict[str, int]:
    """Delete chats and usage events older than the user's configured retention_days (0 = keep forever)."""
    uid = valid_user_id(user_id)
    ret_days = int(get_settings(uid).get("retention_days") or 0)
    if ret_days <= 0:
        return {"usage": 0, "chats": 0}
    cutoff_dt = datetime.now(UTC) - timedelta(days=ret_days)
    init_db()
    with _connect() as conn:
        u_cnt = conn.execute("DELETE FROM usage_events WHERE user_id = ? AND created_at < ?", (uid, cutoff_dt.isoformat())).rowcount
        c_cnt = conn.execute("DELETE FROM saved_chats WHERE user_id = ? AND updated_at < ?", (uid, int(cutoff_dt.timestamp() * 1000))).rowcount
    if u_cnt or c_cnt:
        _compact_sqlite_physical(_db_path())
    return {"usage": u_cnt, "chats": c_cnt}


def wipe_data(user_id: str, scope: str) -> dict[str, int]:
    """SEC-21 Right to Erasure: remove DB rows, FTS index, linked media blobs, and VACUUM/WAL-truncate."""
    from user_profile_helpers import execute_user_wipe

    uid = valid_user_id(user_id)
    if scope not in {"usage", "memories", "conversations", "all"}:
        raise ValueError("Gecersiz kapsam.")
    init_db()
    return execute_user_wipe(uid, scope, _connect, _db_path)


__all__ = [
    "AVATAR_COLORS", "DEFAULT_SETTINGS", "DEFAULT_USER_ID",
    "_compact_sqlite_physical", "_extract_media_filenames", "_fold_tr", "_token_root_match", "_tr_tokens",
    "add_fact", "create_profile", "cross_chat_context_block", "cross_chat_snippets",
    "delete_fact", "delete_profile", "delete_saved_chat", "estimate_tokens", "export_all",
    "get_profile", "get_settings", "init_db", "list_conversations", "list_profiles",
    "list_saved_chats", "personalization_block", "purge_expired_data", "record_usage",
    "sanitize_settings", "update_profile", "upsert_saved_chat", "usage_summary",
    "valid_user_id", "wipe_data",
]
