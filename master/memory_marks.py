"""Pin a remembered fact, give it an end date, or forget it completely.

  hafızamı göster | hafıza 3 sabitle | hafıza 3 sabitlemeyi kaldır | hafıza 3 süre 30 gün | hafıza 3 kalıcı sil

A pinned fact is always given to the model first and never fades. An expired one is forgotten, with its history.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

import memory_engine
import memory_timeline

_SCHEMA = "CREATE TABLE IF NOT EXISTS memory_marks (fact_id INTEGER PRIMARY KEY, pinned INTEGER NOT NULL DEFAULT 0, expires_at TEXT NOT NULL DEFAULT '')"
_LIST_RE = re.compile(r"^\s*(?:hafızamı|hafızayı)\s+(?:göster|listele)\W*$", re.IGNORECASE)
_ACT_RE = re.compile(r"^\s*hafıza\s+#?(?P<id>\d{1,9})\s+(?P<what>sabitle|sabitlemeyi\s+kaldır|kalıcı\s+(?:olarak\s+)?sil|süre\s+(?P<days>\d{1,4})\s+gün)\s*[.!]?\s*$", re.IGNORECASE)


_CLEANUP = "CREATE TRIGGER IF NOT EXISTS memory_marks_cleanup AFTER DELETE ON semantic_memories BEGIN DELETE FROM memory_marks WHERE fact_id = old.id; END"


def _install(conn: sqlite3.Connection) -> None:
    conn.execute(_SCHEMA)
    conn.execute(_CLEANUP)  # a later fact that gets the same id must not inherit the pin or the end date


def _marks(conn: sqlite3.Connection) -> dict[int, tuple[bool, str]]:
    _install(conn)
    return {row["fact_id"]: (bool(row["pinned"]), row["expires_at"]) for row in conn.execute("SELECT fact_id, pinned, expires_at FROM memory_marks")}


def _set(fact_id: int, column: str, value: Any) -> None:
    with memory_engine._connect() as conn:
        _install(conn)
        conn.execute("INSERT OR IGNORE INTO memory_marks (fact_id) VALUES (?)", (fact_id,))
        statement = "UPDATE memory_marks SET pinned = ? WHERE fact_id = ?" if column == "pinned" else "UPDATE memory_marks SET expires_at = ? WHERE fact_id = ?"
        conn.execute(statement, (value, fact_id))


def forget(fact_id: int, user_id: str = "default") -> bool:
    """Remove the fact, its whole history and its marks."""
    with memory_engine._connect() as conn:
        row = conn.execute("SELECT fact_key FROM semantic_memories WHERE id = ? AND user_id = ?", (fact_id, user_id)).fetchone()
        if row is None:
            return False
        _install(conn)
        conn.execute("DELETE FROM memory_marks WHERE fact_id = ?", (fact_id,))
    memory_timeline.purge(row["fact_key"], user_id)
    return True


def apply(facts: list[dict[str, Any]], user_id: str = "default", now: datetime | None = None) -> list[dict[str, Any]]:
    """The facts still valid, pinned ones first; expired ones are forgotten on the way."""
    if not facts:
        return facts
    now_text = (now or datetime.now(UTC)).isoformat()
    with memory_engine._connect() as conn:
        marks = _marks(conn)
    kept = []
    for fact in facts:
        pinned, expires_at = marks.get(fact["id"], (False, ""))
        if expires_at and expires_at <= now_text:
            forget(fact["id"], user_id)
            continue
        kept.append({**fact, "pinned": pinned, "expires_at": expires_at})
    return sorted(kept, key=lambda f: not f["pinned"])


def pinned_ids(conn: sqlite3.Connection) -> set[int]:
    """Read through the caller's own connection; a database that never had a mark has no table yet."""
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'memory_marks'").fetchone() is None:
        return set()
    return {row[0] for row in conn.execute("SELECT fact_id FROM memory_marks WHERE pinned = 1")}


def _listing(user_id: str) -> str:
    facts = memory_engine.list_semantic_facts(user_id)
    if not facts:
        return "Hafızada kayıtlı bilgi yok."
    lines = [f"- #{f['id']} [{f['category']}] {f['fact_value']}" + (" (sabit)" if f.get("pinned") else "") + (f" (bitiş: {f['expires_at'][:10]})" if f.get("expires_at") else "") for f in facts[:40]]
    return "\n".join(["Hafızadaki bilgiler:", *lines, "", "Komutlar: `hafıza <no> sabitle` · `hafıza <no> süre 30 gün` · `hafıza <no> kalıcı sil`"])


def answer(prompt: str, user_id: str = "default") -> str:
    """The reply to a memory command; "" for everything else."""
    if _LIST_RE.match(prompt):
        return _listing(user_id)
    asked = _ACT_RE.match(prompt)
    if asked is None:
        return ""
    fact_id, what = int(asked["id"]), asked["what"].lower()
    if not any(f["id"] == fact_id for f in memory_engine.list_semantic_facts(user_id)):
        return f"#{fact_id} numaralı bir bilgi yok. `hafızamı göster` ile numaralara bak."
    if what.startswith("kalıcı"):
        forget(fact_id, user_id)
        return f"#{fact_id} ve geçmişi kalıcı olarak silindi; geri getirilemez."
    if asked["days"]:
        until = datetime.now(UTC) + timedelta(days=int(asked["days"]))
        _set(fact_id, "expires_at", until.isoformat())
        return f"#{fact_id}, {until:%Y-%m-%d} tarihinde unutulacak."
    _set(fact_id, "pinned", 0 if "kaldır" in what else 1)
    return f"#{fact_id} " + ("artık sabit değil." if "kaldır" in what else "sabitlendi: her zaman dikkate alınacak ve yaşlandıkça silinmeyecek.")
