"""Bi-temporal history of remembered facts: what was true when, and when it was recorded (SQLite triggers).

Overwriting or deleting a fact closes its validity interval instead of losing it; `as_of` answers "what did we know then".
"""

from __future__ import annotations

from typing import Any

import memory_engine

_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS memory_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, category TEXT NOT NULL, fact_key TEXT NOT NULL,
        fact_value TEXT NOT NULL, valid_from TEXT NOT NULL, valid_to TEXT, recorded_at TEXT NOT NULL)""",
    """CREATE TRIGGER IF NOT EXISTS memory_history_insert AFTER INSERT ON semantic_memories BEGIN
        INSERT INTO memory_history (user_id, category, fact_key, fact_value, valid_from, recorded_at)
        VALUES (new.user_id, new.category, new.fact_key, new.fact_value, new.updated_at, new.updated_at); END""",
    """CREATE TRIGGER IF NOT EXISTS memory_history_update AFTER UPDATE OF fact_value ON semantic_memories
        WHEN old.fact_value <> new.fact_value BEGIN
        UPDATE memory_history SET valid_to = new.updated_at WHERE user_id = old.user_id AND category = old.category AND fact_key = old.fact_key AND valid_to IS NULL;
        INSERT INTO memory_history (user_id, category, fact_key, fact_value, valid_from, recorded_at)
        VALUES (new.user_id, new.category, new.fact_key, new.fact_value, new.updated_at, new.updated_at); END""",
    """CREATE TRIGGER IF NOT EXISTS memory_history_delete AFTER DELETE ON semantic_memories BEGIN
        UPDATE memory_history SET valid_to = strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now') WHERE user_id = old.user_id AND category = old.category AND fact_key = old.fact_key AND valid_to IS NULL; END""",
)


def install() -> None:
    memory_engine.init_memory_db()
    with memory_engine._connect() as conn:
        for statement in _SCHEMA:
            conn.execute(statement)


def history(fact_key: str, user_id: str = "default") -> list[dict[str, Any]]:
    """Every value the fact has had, oldest first."""
    install()
    with memory_engine._connect() as conn:
        rows = conn.execute("SELECT fact_value, valid_from, valid_to FROM memory_history WHERE user_id = ? AND fact_key = ? ORDER BY id", (user_id, fact_key)).fetchall()
    return [dict(r) for r in rows]


def as_of(moment: str, user_id: str = "default") -> dict[str, str]:
    """{fact_key: value} that was valid at the ISO timestamp."""
    install()
    with memory_engine._connect() as conn:
        rows = conn.execute("SELECT fact_key, fact_value FROM memory_history WHERE user_id = ? AND valid_from <= ? AND (valid_to IS NULL OR valid_to > ?) ORDER BY id",
                            (user_id, moment, moment)).fetchall()
    return {r["fact_key"]: r["fact_value"] for r in rows}


def purge(fact_key: str, user_id: str = "default") -> int:
    """Forget completely: the current fact and its history."""
    install()
    with memory_engine._connect() as conn:
        conn.execute("DELETE FROM semantic_memories WHERE user_id = ? AND fact_key = ?", (user_id, fact_key))
        return conn.execute("DELETE FROM memory_history WHERE user_id = ? AND fact_key = ?", (user_id, fact_key)).rowcount
