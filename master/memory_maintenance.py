"""Keep the learned-facts table tidy without inventing anything (DAT-09).

Duplicates (the same fact written with different case, accents or spacing) are merged. Two *different*
values for the same fact are never resolved silently: they are returned as conflicts for the user to decide.
Facts also lose weight as they age, and only facts that have faded below a threshold are removed.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime

import search_index


def normalise_key(key: str) -> str:
    return re.sub(r"[\s_\-]+", " ", search_index.fold(key)).strip()


def normalise_value(value: str) -> str:
    return " ".join(search_index.fold(value).split())


def _age_days(updated_at: str, now: datetime) -> float:
    try:
        then = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if then.tzinfo is None:
        then = then.replace(tzinfo=UTC)
    return max(0.0, (now - then).total_seconds() / 86400)


def effective_confidence(confidence: float, updated_at: str, now: datetime, half_life_days: float = 90.0) -> float:
    """Stored confidence halved for every ``half_life_days`` since the fact was last confirmed."""
    return float(confidence) * 0.5 ** (_age_days(updated_at, now) / half_life_days)


def consolidate(conn: sqlite3.Connection, owner: str) -> dict:
    rows = conn.execute(
        "SELECT id, category, fact_key, fact_value, confidence, updated_at FROM semantic_memories WHERE user_id = ?",
        (owner,),
    ).fetchall()
    groups: dict[tuple[str, str], list[sqlite3.Row]] = {}
    for row in rows:
        groups.setdefault((row["category"], normalise_key(row["fact_key"])), []).append(row)
    merged = 0
    conflicts: list[dict] = []
    for (category, key), members in groups.items():
        if len(members) < 2:
            continue
        distinct = {normalise_value(m["fact_value"]) for m in members}
        if len(distinct) == 1:
            keep = max(members, key=lambda m: (m["confidence"], m["updated_at"]))
            for m in members:
                if m["id"] != keep["id"]:
                    conn.execute("DELETE FROM semantic_memories WHERE id = ? AND user_id = ?", (m["id"], owner))
                    merged += 1
        else:
            conflicts.append({
                "category": category, "key": key,
                "candidates": [{"id": m["id"], "value": m["fact_value"], "updated_at": m["updated_at"]} for m in members],
            })
    return {"merged": merged, "conflicts": conflicts}


def resolve_conflict(conn: sqlite3.Connection, owner: str, keep_id: int) -> int:
    """The user picked one candidate: drop the others that share its normalised fact."""
    keep = conn.execute(
        "SELECT category, fact_key FROM semantic_memories WHERE id = ? AND user_id = ?", (keep_id, owner)).fetchone()
    if keep is None:
        raise LookupError(keep_id)
    key = normalise_key(keep["fact_key"])
    removed = 0
    for row in conn.execute(
        "SELECT id, fact_key FROM semantic_memories WHERE user_id = ? AND category = ? AND id != ?",
        (owner, keep["category"], keep_id),
    ).fetchall():
        if normalise_key(row["fact_key"]) == key:
            conn.execute("DELETE FROM semantic_memories WHERE id = ? AND user_id = ?", (row["id"], owner))
            removed += 1
    return removed


def prune_faded(
    conn: sqlite3.Connection, owner: str, now: datetime | None = None, half_life_days: float = 90.0,
    drop_below: float = 0.2,
) -> int:
    import memory_marks  # reads through memory_engine

    moment = now or datetime.now(UTC)
    removed = 0
    pinned = memory_marks.pinned_ids(conn)
    for row in conn.execute(
        "SELECT id, confidence, updated_at FROM semantic_memories WHERE user_id = ?", (owner,)
    ).fetchall():
        if row["id"] not in pinned and effective_confidence(row["confidence"], row["updated_at"], moment, half_life_days) < drop_below:
            conn.execute("DELETE FROM semantic_memories WHERE id = ? AND user_id = ?", (row["id"], owner))
            removed += 1
    return removed
