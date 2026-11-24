"""Querying, pruning and exporting the operational event log (DAT-14).

Events record what happened to agents, tasks and projects (assignment, retry, failure, model promotion).
They are not an audit trail (see audit_log): they may be pruned.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

MAX_PAGE = 500


@dataclass(frozen=True)
class EventQuery:
    event_type: str | None = None
    agent_id: str | None = None
    project_id: int | None = None
    since: str | None = None
    until: str | None = None
    limit: int = 50
    offset: int = 0


def query(
    conn: sqlite3.Connection,
    filters: EventQuery | None = None,
    **kwargs: Any,
) -> list[dict]:
    q = filters if filters is not None else EventQuery(**kwargs)
    rows = conn.execute(
        "SELECT id, project_id, agent_id, event_type, payload, created_at FROM events "
        "WHERE (? IS NULL OR event_type = ?) "
        "AND (? IS NULL OR agent_id = ?) "
        "AND (? IS NULL OR project_id = ?) "
        "AND (? IS NULL OR created_at >= ?) "
        "AND (? IS NULL OR created_at < ?) "
        "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        (
            q.event_type, q.event_type,
            q.agent_id, q.agent_id,
            q.project_id, q.project_id,
            q.since, q.since,
            q.until, q.until,
            max(1, min(q.limit, MAX_PAGE)),
            max(0, q.offset),
        ),
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["payload"] = json.loads(item["payload"]) if item["payload"] else None
        except ValueError:
            pass
        result.append(item)
    return result


def prune(conn: sqlite3.Connection, older_than_days: int = 90, max_rows: int = 200_000) -> int:
    """Delete events past the retention window, then the oldest ones beyond ``max_rows``."""
    cutoff = (datetime.now(UTC) - timedelta(days=older_than_days)).isoformat(timespec="seconds")
    removed = conn.execute("DELETE FROM events WHERE created_at < ?", (cutoff,)).rowcount
    excess = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] - max_rows
    if excess > 0:
        removed += conn.execute(
            "DELETE FROM events WHERE id IN (SELECT id FROM events ORDER BY created_at, id LIMIT ?)", (excess,)
        ).rowcount
    return removed


def export_jsonl(conn: sqlite3.Connection, destination: Path, since: str | None = None) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with destination.open("w", encoding="utf-8") as out:
        offset = 0
        while True:
            page = query(conn, since=since, limit=MAX_PAGE, offset=offset)
            if not page:
                break
            for item in reversed(page):
                out.write(json.dumps(item, ensure_ascii=False) + "\n")
            count += len(page)
            offset += MAX_PAGE
    return count
