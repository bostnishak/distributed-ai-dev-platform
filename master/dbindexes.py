"""Indexes for the queries the application runs most, plus the catalogue that proves they are used (DAT-13).

``QUERIES`` lists the hot queries; a test asks SQLite for each query plan and fails on a full table scan, so a
new hot query without an index shows up before it is slow with a million rows.
"""

from __future__ import annotations

import sqlite3

import ownership

INDEXES: tuple[tuple[str, str, str], ...] = (
    ("idx_conversations_user", "conversations", "user_id, updated_at"),
    ("idx_messages_conversation", "conversation_messages", "conversation_id, id"),
    ("idx_memories_user", "semantic_memories", "user_id, category"),
    ("idx_saved_chats_user", "saved_chats", "user_id, updated_at"),
    ("idx_usage_user_ts", "usage_events", "user_id, ts"),
)

# name -> (sql, params); every one must be answered from an index.
QUERIES: dict[str, tuple[str, tuple]] = {
    "chats of a user, newest first": (
        "SELECT id, title FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT 50", ("u",)),
    "messages of a chat": ("SELECT role, content FROM conversation_messages WHERE conversation_id = ? ORDER BY id", ("c",)),
    "facts of a user": ("SELECT fact_key, fact_value FROM semantic_memories WHERE user_id = ? AND category = ?", ("u", "k")),
    "saved chats of a user": ("SELECT chat_id, title FROM saved_chats WHERE user_id = ? ORDER BY updated_at DESC", ("u",)),
    "usage of a user since a date": ("SELECT COUNT(*) FROM usage_events WHERE user_id = ? AND ts >= ?", ("u", "2026")),
    "tasks of a project by status": ("SELECT id FROM tasks WHERE project_id = ? AND status = ?", (1, "planned")),
    "recent events by type": (
        "SELECT id FROM events WHERE event_type = ? AND created_at >= ? ORDER BY created_at DESC LIMIT 50", ("t", "2026")),
    "files of an owner": ("SELECT id, name FROM files WHERE owner_id = ? ORDER BY created_at", ("u",)),
    "files by content hash": ("SELECT id FROM files WHERE sha256 = ?", ("x",)),
}


def ensure_indexes(conn: sqlite3.Connection) -> list[str]:
    """Create each index whose table exists in this database; returns the names created or already present."""
    present = ownership.table_names(conn)
    done = []
    for name, table, columns in INDEXES:
        wanted = {c.strip() for c in columns.split(",")}
        if table in present and wanted <= {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}:
            conn.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table}({columns})")
            done.append(name)
    return done


def full_scans(conn: sqlite3.Connection, sql: str, params: tuple) -> list[str]:
    """Plan steps that read a whole table instead of using an index."""
    plan = [row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + sql, params)]
    return [step for step in plan if step.startswith("SCAN ") and "USING" not in step and "VIRTUAL" not in step]


def paginate(conn: sqlite3.Connection, sql: str, params: tuple = (), page: int = 1, size: int = 50) -> dict:
    """Offset pagination with a hard size cap; ``sql`` must already have a deterministic ORDER BY."""
    size = max(1, min(int(size), 200))
    page = max(1, int(page))
    rows = conn.execute(f"{sql} LIMIT ? OFFSET ?", (*params, size + 1, (page - 1) * size)).fetchall()
    return {"rows": rows[:size], "page": page, "size": size, "has_more": len(rows) > size}
