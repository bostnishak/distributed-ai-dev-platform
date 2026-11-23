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

import config
import memory_engine

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
    p = Path(config.DATA_DIR) / "user_profile.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                role_title TEXT NOT NULL DEFAULT '',
                bio TEXT NOT NULL DEFAULT '',
                avatar_color TEXT NOT NULL DEFAULT '#4f46e5',
                settings_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                conversation_id TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                task_type TEXT NOT NULL DEFAULT '',
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                latency_ms INTEGER NOT NULL DEFAULT 0,
                estimated INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_usage_user_ts ON usage_events(user_id, ts);
            CREATE TABLE IF NOT EXISTS saved_chats (
                chat_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT 'Yeni sohbet',
                updated_at INTEGER NOT NULL DEFAULT 0,
                messages_json TEXT NOT NULL DEFAULT '[]',
                PRIMARY KEY (user_id, chat_id)
            );
            CREATE INDEX IF NOT EXISTS idx_saved_chats_user_updated ON saved_chats(user_id, updated_at DESC);
            """
        )


def valid_user_id(user_id: str) -> str:
    uid = (user_id or DEFAULT_USER_ID).strip().lower()
    if not _UID_RE.match(uid):
        raise ValueError("Gecersiz profil kimligi.")
    return uid


def sanitize_settings(patch: dict[str, Any]) -> dict[str, Any]:
    """Keep only known keys with valid values; unknown or invalid entries are dropped."""
    clean: dict[str, Any] = {}
    for key, value in (patch or {}).items():
        if key in _ENUMS:
            if isinstance(value, str) and value in _ENUMS[key]:
                clean[key] = value
        elif key in _BOOLS:
            if isinstance(value, bool):
                clean[key] = value
        elif key in _TEXT_LIMITS:
            if isinstance(value, str):
                clean[key] = value.strip()[: _TEXT_LIMITS[key]]
        elif key == "monthly_token_budget":
            try:
                clean[key] = max(0, min(int(value), 1_000_000_000))
            except (TypeError, ValueError):
                continue
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


def update_profile(
    user_id: str,
    display_name: str | None = None,
    role_title: str | None = None,
    bio: str | None = None,
    avatar_color: str | None = None,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
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


def record_usage(
    user_id: str,
    conversation_id: str,
    model: str,
    task_type: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    estimated: bool = False,
) -> None:
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
                model or "",
                task_type or "",
                max(0, int(prompt_tokens)),
                max(0, int(completion_tokens)),
                max(0, int(latency_ms)),
                1 if estimated else 0,
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

    daily = {(start + timedelta(days=i)).isoformat(): {"tokens": 0, "messages": 0} for i in range(days)}
    by_model: dict[str, dict[str, int]] = {}
    by_task: dict[str, dict[str, int]] = {}
    by_hour = [0] * 24
    prompt_total = completion_total = latency_total = 0
    conversations: set[str] = set()
    for r in rows:
        tokens = r["prompt_tokens"] + r["completion_tokens"]
        day = r["ts"][:10]
        if day in daily:
            daily[day]["tokens"] += tokens
            daily[day]["messages"] += 1
        for bucket, key in ((by_model, r["model"] or "bilinmiyor"), (by_task, r["task_type"] or "genel")):
            slot = bucket.setdefault(key, {"messages": 0, "tokens": 0})
            slot["messages"] += 1
            slot["tokens"] += tokens
        try:
            by_hour[datetime.fromisoformat(r["ts"]).astimezone().hour] += 1
        except ValueError:
            pass
        prompt_total += r["prompt_tokens"]
        completion_total += r["completion_tokens"]
        latency_total += r["latency_ms"]
        if r["conversation_id"]:
            conversations.add(r["conversation_id"])

    messages = len(rows)
    total_tokens = prompt_total + completion_total

    used_days = {x["d"] for x in all_days}
    streak = 0
    cursor = today
    if cursor.isoformat() not in used_days:
        cursor -= timedelta(days=1)
    while cursor.isoformat() in used_days:
        streak += 1
        cursor -= timedelta(days=1)

    budget = int(get_settings(uid).get("monthly_token_budget") or 0)
    return {
        "user_id": uid,
        "days": days,
        "totals": {
            "messages": messages,
            "conversations": len(conversations),
            "prompt_tokens": prompt_total,
            "completion_tokens": completion_total,
            "total_tokens": total_tokens,
            "avg_tokens_per_message": round(total_tokens / messages) if messages else 0,
            "avg_latency_ms": round(latency_total / messages) if messages else 0,
            "streak_days": streak,
            "active_days": len(used_days),
        },
        "daily": [{"date": d, **v} for d, v in daily.items()],
        "by_model": sorted(
            ({"model": k, **v} for k, v in by_model.items()), key=lambda x: x["tokens"], reverse=True
        ),
        "by_task": sorted(
            ({"task_type": k, **v} for k, v in by_task.items()), key=lambda x: x["messages"], reverse=True
        ),
        "by_hour": by_hour,
        "budget": {
            "monthly_token_budget": budget,
            "month_tokens": int(month_tokens),
            "percent": round(month_tokens / budget * 100, 1) if budget else 0.0,
        },
        # Hypothetical reference only: what the same volume would cost on a paid cloud API
        # (assumed 1 USD per 1M input and 4 USD per 1M output tokens). Local use costs nothing.
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
    """Full-text search over this user's other conversations."""
    memory_engine.init_memory_db()
    uid = valid_user_id(user_id)
    tokens = [t for t in re.findall(r"[A-Za-z0-9ÇĞİÖŞÜçğıöşü]+", query or "") if len(t) > 2]
    if not tokens:
        return []
    fts_q = " OR ".join(f'"{t}"' for t in tokens[:6])
    conn = memory_engine._connect()
    try:
        rows = conn.execute(
            """
            SELECT f.conversation_id AS conversation_id, c.title AS title, f.role AS role,
                   snippet(messages_fts, 2, '[', ']', '...', 28) AS snippet
            FROM messages_fts f
            JOIN conversations c ON c.id = f.conversation_id
            WHERE messages_fts MATCH ? AND c.user_id = ? AND f.conversation_id != ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_q, uid, exclude_conversation or "", max(1, min(limit, 20))),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


_TR_FOLD = str.maketrans("ÇĞİÖŞÜçğıöşüİ", "cgiosucgiosui")

_CROSS_CHAT_CUES = (
    "sohbet",
    "chat",
    "gecmis",
    "diger",
    "onceki",
    "adli",
    "baslikli",
    "karsilastir",
    "birlestir",
    "aktar",
    "prompt",
    "analiz",
    "oku",
)

_GENERIC_RECENT_CUES = (
    "diger sohbet",
    "diger chat",
    "onceki sohbet",
    "onceki chat",
    "son sohbet",
    "son chat",
    "tum sohbet",
    "butun sohbet",
    "iki sohbet",
    "2 sohbet",
    "2 chat",
    "iki chat",
)


def _fold_tr(text: str) -> str:
    return (text or "").translate(_TR_FOLD).lower()


def _tr_tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", _fold_tr(text)) if len(t) > 2]


def _token_root_match(q_tok: str, t_tok: str) -> bool:
    if q_tok == t_tok:
        return True
    if len(q_tok) >= 4 and len(t_tok) >= 4:
        root_len = min(5, len(q_tok), len(t_tok))
        if q_tok[:root_len] == t_tok[:root_len]:
            return True
    return False


def cross_chat_context_block(user_id: str, query: str, exclude_conversation: str = "") -> str:
    """Provide a directory of saved chats and inject full transcripts of referenced/matched chats."""
    uid = valid_user_id(user_id)
    saved = list_saved_chats(uid)
    other_chats = [
        (cid, rec)
        for cid, rec in saved.items()
        if cid != (exclude_conversation or "") and (rec.get("messages") or [])
    ]

    q_folded = _fold_tr(query or "")
    q_tokens = _tr_tokens(query or "")
    explicit_ref = any(cue in q_folded for cue in _CROSS_CHAT_CUES)
    generic_recent = any(cue in q_folded for cue in _GENERIC_RECENT_CUES)

    lines: list[str] = []

    if other_chats:
        # Always expose a compact directory of the user's saved chats so the AI can reason across them
        lines.append("--- Kullanicinin Kayitli Diger Sohbetleri ---")
        for _cid, rec in other_chats[:15]:
            title = (rec.get("title") or "Sohbet").strip()
            msg_count = len(rec.get("messages") or [])
            lines.append(f"- \"{title}\" ({msg_count} mesaj)")

        # Score chats against the query (title match + content overlap)
        scored: list[tuple[int, str, dict[str, Any]]] = []
        for cid, rec in other_chats:
            title = (rec.get("title") or "").strip()
            title_folded = _fold_tr(title)
            title_tokens = _tr_tokens(title)
            score = 0
            if title_folded and len(title_folded) >= 4 and title_folded in q_folded:
                score += 30
            for qt in q_tokens:
                if any(_token_root_match(qt, tt) for tt in title_tokens):
                    score += 8
            if explicit_ref or score > 0:
                msg_blob = " ".join(str(m.get("text") or "")[:400] for m in (rec.get("messages") or [])[:12])
                msg_tokens = set(_tr_tokens(msg_blob))
                overlap = sum(1 for qt in q_tokens if any(_token_root_match(qt, mt) for mt in msg_tokens))
                score += min(overlap * 2, 14)
            if score > 0:
                scored.append((score, cid, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected: list[tuple[str, dict[str, Any]]] = [(cid, rec) for _sc, cid, rec in scored[:3]]

        if not selected and (generic_recent or explicit_ref):
            # User asked about "previous/other chat" without quoting exact title: load 2 most recent
            selected = other_chats[:2]

        if selected:
            lines.append("")
            lines.append(
                "--- Eslesen Diger Sohbet Gecmisleri (Kullanici bu sohbetleri okumani, analiz etmeni, "
                "karsilastirmani veya buna gore istemini degistirmeni istediginde dogrudan kullan) ---"
            )
            char_budget = 6000
            used_chars = 0
            for _cid, rec in selected:
                title = (rec.get("title") or "Sohbet").strip()
                msgs = rec.get("messages") or []
                header = f"\n### Sohbet: \"{title}\" ({len(msgs)} mesaj)"
                lines.append(header)
                used_chars += len(header)
                for m in msgs[-16:]:
                    role_lbl = "Kullanici" if m.get("role") == "user" else "Asistan"
                    body = str(m.get("text") or "").strip()
                    if len(body) > 750:
                        body = body[:750] + "..."
                    entry = f"{role_lbl}: {body}"
                    if used_chars + len(entry) > char_budget:
                        lines.append("[... kalan kisim ozetlendi ...]")
                        break
                    lines.append(entry)
                    used_chars += len(entry)
                if used_chars >= char_budget:
                    break

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
    return [dict(r) for r in rows]


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
    uid = valid_user_id(user_id)
    conv_conn = memory_engine._connect()
    try:
        memory_engine.init_memory_db()
        convs = []
        for c in list_conversations(uid, limit=200):
            msgs = conv_conn.execute(
                "SELECT role, content, model_used, task_type, created_at FROM conversation_messages "
                "WHERE conversation_id = ? ORDER BY id",
                (c["id"],),
            ).fetchall()
            convs.append({**c, "messages": [dict(m) for m in msgs]})
    finally:
        conv_conn.close()
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "profile": get_profile(uid),
        "memories": memory_engine.list_semantic_facts(user_id=uid),
        "usage": usage_summary(uid, days=365),
        "conversations": convs,
        "saved_chats": list_saved_chats(uid),
    }


def wipe_data(user_id: str, scope: str) -> dict[str, int]:
    """scope: usage | memories | conversations | all"""
    uid = valid_user_id(user_id)
    if scope not in {"usage", "memories", "conversations", "all"}:
        raise ValueError("Gecersiz kapsam.")
    init_db()
    memory_engine.init_memory_db()
    removed = {"usage": 0, "memories": 0, "conversations": 0}
    if scope in {"usage", "all"}:
        with _connect() as conn:
            removed["usage"] = conn.execute("DELETE FROM usage_events WHERE user_id = ?", (uid,)).rowcount
    if scope in {"conversations", "all"}:
        with _connect() as conn:
            conn.execute("DELETE FROM saved_chats WHERE user_id = ?", (uid,))
    mconn = memory_engine._connect()
    try:
        with mconn:
            if scope in {"memories", "all"}:
                removed["memories"] = mconn.execute(
                    "DELETE FROM semantic_memories WHERE user_id = ?", (uid,)
                ).rowcount
            if scope in {"conversations", "all"}:
                ids = [r["id"] for r in mconn.execute("SELECT id FROM conversations WHERE user_id = ?", (uid,))]
                for cid in ids:
                    mconn.execute("DELETE FROM messages_fts WHERE conversation_id = ?", (cid,))
                    mconn.execute("DELETE FROM conversation_messages WHERE conversation_id = ?", (cid,))
                    mconn.execute("DELETE FROM conversations WHERE id = ?", (cid,))
                removed["conversations"] = len(ids)
    finally:
        mconn.close()
    return removed
