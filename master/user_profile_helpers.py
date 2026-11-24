"""Helper routines for `user_profile.py`: Turkish cross-chat search, usage aggregation & SEC-21 erasure."""

from __future__ import annotations

import logging
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import config
import memory_engine

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

_TRIVIAL_GREETINGS = {
    "selam",
    "merhaba",
    "hey",
    "hi",
    "hello",
    "nasilsin",
    "naber",
    "gunaydin",
    "iyi aksamlar",
    "iyi geceler",
    "test",
    "deneme",
    "tesekkurler",
    "sag ol",
    "tamam",
    "ok",
}


def fold_tr(text: str) -> str:
    return (text or "").translate(_TR_FOLD).lower()


def tr_tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", fold_tr(text)) if len(t) > 2]


def token_root_match(q_tok: str, t_tok: str) -> bool:
    if q_tok == t_tok:
        return True
    if len(q_tok) >= 4 and len(t_tok) >= 4:
        root_len = min(5, len(q_tok), len(t_tok))
        if q_tok[:root_len] == t_tok[:root_len]:
            return True
    return False


def is_trivial_query(q_folded: str) -> bool:
    return not q_folded or q_folded in _TRIVIAL_GREETINGS


def has_cross_chat_cue(q_folded: str) -> tuple[bool, bool]:
    explicit_ref = any(cue in q_folded for cue in _CROSS_CHAT_CUES)
    generic_recent = any(cue in q_folded for cue in _GENERIC_RECENT_CUES)
    return explicit_ref, generic_recent


def sanitize_bounded_int(value: Any, upper: int) -> int | None:
    try:
        return max(0, min(int(value), upper))
    except (TypeError, ValueError):
        return None


def _match_saved_message(body: str, q_folded: str, q_tokens: list[str]) -> str | None:
    body_folded = fold_tr(body)
    matched = q_folded in body_folded or (
        bool(q_tokens) and any(token_root_match(qt, bt) for qt in q_tokens for bt in tr_tokens(body[:1200]))
    )
    if not matched:
        return None
    idx = body_folded.find(q_folded) if q_folded in body_folded else 0
    start = max(0, idx - 45)
    prefix = "..." if start > 0 else ""
    suffix = "..." if start + 140 < len(body) else ""
    return prefix + body[start : start + 140].replace("\n", " ") + suffix


def search_saved_chats_snippets(
    saved: dict[str, dict[str, Any]],
    raw_q: str,
    exclude_conversation: str,
    cap: int,
) -> tuple[list[dict[str, str]], set[tuple[str, str]]]:
    q_folded = fold_tr(raw_q)
    q_tokens = tr_tokens(raw_q)
    results: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for cid, rec in saved.items():
        if cid == (exclude_conversation or ""):
            continue
        title = (rec.get("title") or "Sohbet").strip()
        for m in rec.get("messages") or []:
            body = str(m.get("text") or "").strip()
            if not body:
                continue
            snip = _match_saved_message(body, q_folded, q_tokens)
            if snip is None:
                continue
            key = (cid, snip[:48])
            if key not in seen:
                seen.add(key)
                results.append({"conversation_id": cid, "title": title, "role": str(m.get("role") or "user"), "snippet": snip})
                if len(results) >= cap:
                    return results, seen
    return results, seen


def search_fts_snippets(
    uid: str,
    raw_q: str,
    exclude_conversation: str,
    cap: int,
    seen: set[tuple[str, str]],
) -> list[dict[str, str]]:
    tokens = [t for t in re.findall(r"[A-Za-z0-9ÇĞİÖŞÜçğıöşü]+", raw_q) if len(t) > 2]
    if not tokens:
        return []
    fts_q = " OR ".join(f'"{t}"' for t in tokens[:6])
    out: list[dict[str, str]] = []
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
            (fts_q, uid, exclude_conversation or "", cap),
        ).fetchall()
        for r in rows:
            d = dict(r)
            key = (d["conversation_id"], str(d["snippet"])[:48])
            if key not in seen:
                seen.add(key)
                out.append(d)
                if len(out) >= cap:
                    break
    except (sqlite3.Error, OSError, ValueError, KeyError, TypeError) as exc:
        logging.getLogger(__name__).debug("Recoverable error suppressed: %s", exc)
    finally:
        conn.close()
    return out


def _score_chat_entry(rec: dict[str, Any], q_folded: str, q_tokens: list[str], explicit_ref: bool) -> int:
    title = (rec.get("title") or "").strip()
    title_folded = fold_tr(title)
    title_tokens = tr_tokens(title)
    score = 30 if (title_folded and len(title_folded) >= 4 and title_folded in q_folded) else 0
    for qt in q_tokens:
        if any(token_root_match(qt, tt) for tt in title_tokens):
            score += 8
    if explicit_ref or score > 0:
        msg_blob = " ".join(str(m.get("text") or "")[:400] for m in (rec.get("messages") or [])[:12])
        msg_tokens = set(tr_tokens(msg_blob))
        overlap = sum(1 for qt in q_tokens if any(token_root_match(qt, mt) for mt in msg_tokens))
        score += min(overlap * 2, 14)
    return score


def select_relevant_chats(
    other_chats: list[tuple[str, dict[str, Any]]],
    q_folded: str,
    q_tokens: list[str],
    explicit_ref: bool,
    generic_recent: bool,
) -> list[tuple[str, dict[str, Any]]]:
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for cid, rec in other_chats:
        score = _score_chat_entry(rec, q_folded, q_tokens, explicit_ref)
        if score > 0:
            scored.append((score, cid, rec))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [(cid, rec) for _sc, cid, rec in scored[:3]]
    if not selected and (generic_recent or explicit_ref):
        return other_chats[:2]
    return selected


def format_selected_chats_lines(selected: list[tuple[str, dict[str, Any]]], char_budget: int = 6000) -> list[str]:
    if not selected:
        return []
    lines = [
        "",
        "--- Eslesen Diger Sohbet Gecmisleri (Kullanici bu sohbetleri okumani, analiz etmeni, "
        "karsilastirmani veya buna gore istemini degistirmeni istediginde dogrudan kullan) ---",
    ]
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
    return lines


def compute_usage_buckets(
    rows: list[sqlite3.Row],
    start: date,
    days: int,
    all_days: list[sqlite3.Row],
    today: date,
) -> dict[str, Any]:
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

    used_days = {x["d"] for x in all_days}
    streak = 0
    cursor = today if today.isoformat() in used_days else today - timedelta(days=1)
    while cursor.isoformat() in used_days:
        streak += 1
        cursor -= timedelta(days=1)
    return {
        "daily": daily,
        "by_model": by_model,
        "by_task": by_task,
        "by_hour": by_hour,
        "prompt_total": prompt_total,
        "completion_total": completion_total,
        "latency_total": latency_total,
        "conversations": conversations,
        "streak": streak,
        "active_days": len(used_days),
    }


def compact_sqlite_physical(db_path: Path) -> None:
    """Force WAL truncation and VACUUM so erased user data leaves zero residual bytes on disk (SEC-21)."""
    if not db_path.is_file():
        return
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("VACUUM")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()


def extract_media_filenames(text: str) -> set[str]:
    return set(re.findall(r"/api/assistant/media/([A-Za-z0-9._\-]+)", text or ""))


def wipe_memory_tables(uid: str, scope: str, media_to_delete: set[str]) -> tuple[int, int]:
    memories_removed = 0
    convs_removed = 0
    mconn = memory_engine._connect()
    try:
        with mconn:
            if scope in {"memories", "all"}:
                memories_removed = mconn.execute(
                    "DELETE FROM semantic_memories WHERE user_id = ?", (uid,)
                ).rowcount
            if scope in {"conversations", "all"}:
                ids = [r["id"] for r in mconn.execute("SELECT id FROM conversations WHERE user_id = ?", (uid,))]
                for cid in ids:
                    for mr in mconn.execute("SELECT content FROM conversation_messages WHERE conversation_id = ?", (cid,)):
                        media_to_delete.update(extract_media_filenames(str(mr["content"] or "")))
                    mconn.execute("DELETE FROM messages_fts WHERE conversation_id = ?", (cid,))
                    mconn.execute("DELETE FROM conversation_messages WHERE conversation_id = ?", (cid,))
                    mconn.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (cid, uid))
                convs_removed = len(ids)
    finally:
        mconn.close()
    return memories_removed, convs_removed


def delete_user_media_files(media_to_delete: set[str]) -> int:
    media_root = Path(config.DATA_DIR) / "media"
    media_resolved = media_root.resolve()
    removed_count = 0
    for fname in media_to_delete:
        target = (media_root / Path(fname).name).resolve()
        if media_resolved in target.parents and target.is_file():
            try:
                target.unlink()
                removed_count += 1
            except OSError:
                continue
    return removed_count


def export_conversations_with_messages(conv_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conv_conn = memory_engine._connect()
    try:
        memory_engine.init_memory_db()
        convs = []
        for c in conv_list:
            msgs = conv_conn.execute(
                "SELECT role, content, model_used, task_type, created_at FROM conversation_messages "
                "WHERE conversation_id = ? ORDER BY id",
                (c["id"],),
            ).fetchall()
            convs.append({**c, "messages": [dict(m) for m in msgs]})
        return convs
    finally:
        conv_conn.close()


def execute_user_wipe(uid: str, scope: str, connect_fn: Any, db_path_fn: Any) -> dict[str, int]:
    import dbconn

    memory_engine.init_memory_db()
    removed = {"usage": 0, "memories": 0, "conversations": 0, "media_files": 0}
    media_to_delete: set[str] = set()
    if scope in {"usage", "all"}:
        with connect_fn() as conn:
            removed["usage"] = conn.execute("DELETE FROM usage_events WHERE user_id = ?", (uid,)).rowcount
    if scope in {"conversations", "all"}:
        with connect_fn() as conn:
            rows = conn.execute("SELECT messages_json FROM saved_chats WHERE user_id = ?", (uid,)).fetchall()
            for r in rows:
                media_to_delete.update(extract_media_filenames(str(r["messages_json"] or "")))
            conn.execute("DELETE FROM saved_chats WHERE user_id = ?", (uid,))
    removed["memories"], removed["conversations"] = wipe_memory_tables(uid, scope, media_to_delete)
    removed["media_files"] = delete_user_media_files(media_to_delete)
    compact_sqlite_physical(db_path_fn())
    compact_sqlite_physical(dbconn.database_file("cognitive_memory.db"))
    try:
        from audit_log import AuditTrail

        AuditTrail().append_event(actor=uid, action="USER_DATA_WIPED", payload={"user_id": uid, "scope": scope, "removed": removed})
    except (ImportError, OSError, ValueError, TypeError, RuntimeError) as exc:
        logging.getLogger(__name__).debug("Recoverable error suppressed: %s", exc)
    return removed
