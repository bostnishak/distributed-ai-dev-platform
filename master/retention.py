"""Retention policies and complete erasure of a user's data (DAT-06).

A policy says how many days to keep chats, usage records and files; ``purge_expired`` applies it. ``erase_user``
removes every row the user owns from every database file, collects the blobs nothing references any more, and
rewrites the files so deleted text cannot be read back from free pages or the write-ahead log.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import blobstore
import config
import dbconn
import ownership

LEGACY_NAMES = ("user_profile.db", "cognitive_memory.db", "graph_rag.db", "cmm_quality.db")


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def set_policy(
    conn: sqlite3.Connection, owner: str, chat_days: int | None = None, usage_days: int | None = None,
    file_days: int | None = None,
) -> None:
    for days in (chat_days, usage_days, file_days):
        if days is not None and days < 1:
            raise ValueError("saklama süresi en az 1 gün olmalı (süresiz için boş bırakın)")
    conn.execute(
        "INSERT INTO retention_policies (owner_id, chat_days, usage_days, file_days, updated_at) VALUES (?,?,?,?,?) "
        "ON CONFLICT(owner_id) DO UPDATE SET chat_days = excluded.chat_days, usage_days = excluded.usage_days, "
        "file_days = excluded.file_days, updated_at = excluded.updated_at",
        (owner, chat_days, usage_days, file_days, _iso(_now())),
    )


def get_policy(conn: sqlite3.Connection, owner: str) -> dict:
    row = conn.execute("SELECT * FROM retention_policies WHERE retention_policies.owner_id = ?", (owner,)).fetchone()
    if row is None:
        return {"owner_id": owner, "chat_days": None, "usage_days": None, "file_days": None}
    return dict(row)


def _has(conn: sqlite3.Connection, table: str) -> bool:
    return table in ownership.table_names(conn)


def _purge_chats(conn: sqlite3.Connection, owner: str, cutoff: str) -> int:
    if not _has(conn, "conversations"):
        return 0
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM conversations WHERE user_id = ? AND updated_at < ?", (owner, cutoff))]
    for cid in ids:
        conn.execute("DELETE FROM conversation_messages WHERE conversation_id = ?", (cid,))
        try:
            conn.execute("DELETE FROM messages_fts WHERE conversation_id = ?", (cid,))
        except sqlite3.OperationalError:
            pass
        if _has(conn, "search_index"):
            conn.execute("DELETE FROM search_index WHERE kind = 'chat' AND owner_id = ? AND ref = ?", (owner, cid))
        conn.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (cid, owner))
    if _has(conn, "saved_chats"):
        conn.execute("DELETE FROM saved_chats WHERE user_id = ? AND updated_at < ?", (owner, cutoff))
    return len(ids)


def purge_expired(conn: sqlite3.Connection, now: datetime | None = None) -> dict[str, int]:
    """Apply every owner's policy, drop expired files and collect unreferenced blobs."""
    moment = now or _now()
    removed = {"chats": 0, "usage_events": 0, "files": 0}
    if _has(conn, "retention_policies"):
        for policy in conn.execute("SELECT * FROM retention_policies").fetchall():
            owner = policy["owner_id"]
            if policy["chat_days"]:
                removed["chats"] += _purge_chats(conn, owner, _iso(moment - timedelta(days=policy["chat_days"])))
            if policy["usage_days"] and _has(conn, "usage_events"):
                cutoff = _iso(moment - timedelta(days=policy["usage_days"]))
                removed["usage_events"] += conn.execute(
                    "DELETE FROM usage_events WHERE user_id = ? AND ts < ?", (owner, cutoff)).rowcount
            if policy["file_days"] and _has(conn, "files"):
                cutoff = _iso(moment - timedelta(days=policy["file_days"]))
                removed["files"] += conn.execute(
                    "DELETE FROM files WHERE owner_id = ? AND created_at < ?", (owner, cutoff)).rowcount
    if _has(conn, "files"):
        removed.update({f"gc_{k}": v for k, v in blobstore.collect_garbage(conn).items()})
    return removed


def database_files() -> list[Path]:
    """Every SQLite file that may hold user data in the current layout."""
    candidates = [Path(config.DB_PATH), *(dbconn.data_dir() / name for name in LEGACY_NAMES)]
    return [p for p in dict.fromkeys(candidates) if p.is_file()]


def compact(path: Path) -> None:
    """Truncate the write-ahead log and rebuild the file so deleted rows leave no readable bytes behind."""
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("VACUUM")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()


def erase_user(owner: str, *, compact_files: bool = True) -> dict[str, dict[str, int]]:
    """Delete everything ``owner`` has, everywhere; returns rows removed per database file."""
    report: dict[str, dict[str, int]] = {}
    platform_changed = False
    for path in database_files():
        with dbconn.connection(path) as conn:
            counts = ownership.delete_owner(conn, owner)
            if _has(conn, "files"):
                counts.update({f"gc_{k}": v for k, v in blobstore.collect_garbage(conn).items()})
                platform_changed = True
            report[path.name] = counts
    if compact_files:
        for path in database_files():
            compact(path)
    report["_platform_blob_gc"] = {"ran": int(platform_changed)}
    return report
