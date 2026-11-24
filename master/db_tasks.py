"""Task queue, conflicts, events, and performance statistics queries for `db.py`."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import config
import dbconn

MAX_ATTEMPTS = 3  # PB-44: tasks fail permanently after this many attempts


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@contextmanager
def _connect():
    conn = dbconn.open_db(config.DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def assign_task(task_id: int, agent_id: str, reason: dict, lease_minutes: int = 5) -> None:
    now = datetime.now(UTC)
    expires = (now + timedelta(minutes=lease_minutes)).isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            "UPDATE tasks SET assigned_to = ?, assigned_at = ?, lease_expires_at = ?, "
            "assignment_reason = ?, status = 'planned' WHERE id = ?",
            (agent_id, now.isoformat(timespec="seconds"), expires, json.dumps(reason), task_id),
        )


def get_next_task_for_agent(agent_id: str) -> dict | None:
    """Return the next assigned planned task for this agent, or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE assigned_to = ? AND status = 'planned' "
            "ORDER BY stage, id LIMIT 1",
            (agent_id,),
        ).fetchone()
    if row is None:
        return None
    task = dict(row)
    task["details"] = json.loads(task["details"])
    return task


def get_task(task_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return None
    task = dict(row)
    task["details"] = json.loads(task["details"])
    return task


def submit_task_result(task_id: int, status: str, output: str, tokens_per_second: float | None) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE tasks SET status = ?, result = ?, result_at = ?, tokens_per_second = ? WHERE id = ?",
            (status, output, _utc_now(), tokens_per_second, task_id),
        )


def expire_stale_leases() -> int:
    """Reset tasks whose lease has expired back to planned (unassigned)."""
    now = _utc_now()
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET assigned_to = NULL, assigned_at = NULL, lease_expires_at = NULL, "
            "assignment_reason = NULL WHERE status = 'planned' AND lease_expires_at IS NOT NULL "
            "AND lease_expires_at < ?",
            (now,),
        )
        return cursor.rowcount


def list_unassigned_planned_tasks() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = 'planned' AND assigned_to IS NULL ORDER BY stage, id"
        ).fetchall()
    result = []
    for row in rows:
        task = dict(row)
        task["details"] = json.loads(task["details"])
        result.append(task)
    return result


def submit_task_result_with_files(
    task_id: int,
    status: str,
    output: str,
    files: list[dict] | None,
    tokens_per_second: float | None,
    **options: Any,
) -> None:
    """Submit task result including optional files list. Records perf_ms from assignment."""
    performed_by: str | None = options.get("performed_by")
    with _connect() as conn:
        row = conn.execute("SELECT assigned_at FROM tasks WHERE id = ?", (task_id,)).fetchone()
        perf_ms: int | None = None
        if row and row["assigned_at"]:
            try:
                assigned = datetime.fromisoformat(row["assigned_at"].replace("Z", "+00:00"))
                if assigned.tzinfo is None:
                    assigned = assigned.replace(tzinfo=UTC)
                perf_ms = int((datetime.now(UTC) - assigned).total_seconds() * 1000)
            except (ValueError, TypeError):
                pass
        conn.execute(
            "UPDATE tasks SET status = ?, result = ?, result_at = ?, tokens_per_second = ?, "
            "files = ?, attempt = attempt + 1, perf_ms = ?, performed_by = COALESCE(?, performed_by) WHERE id = ?",
            (
                status,
                output,
                _utc_now(),
                tokens_per_second,
                json.dumps(files, ensure_ascii=False) if files else None,
                perf_ms,
                performed_by,
                task_id,
            ),
        )


def update_task_validation(task_id: int, validation_status: str, message: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE tasks SET validation_status = ?, validation_message = ? WHERE id = ?",
            (validation_status, message, task_id),
        )


def requeue_task(task_id: int, max_attempts: int = MAX_ATTEMPTS) -> str:
    """Reset a task to planned, or mark it permanently failed if MAX_ATTEMPTS reached.

    Returns 'requeued' or 'failed'.
    """
    with _connect() as conn:
        row = conn.execute("SELECT attempt FROM tasks WHERE id = ?", (task_id,)).fetchone()
        current_attempt = (row["attempt"] or 0) if row else 0
        if current_attempt >= max_attempts:
            conn.execute(
                "UPDATE tasks SET status = 'failed', assigned_to = NULL, assigned_at = NULL, "
                "lease_expires_at = NULL WHERE id = ?",
                (task_id,),
            )
            return "failed"
        conn.execute(
            "UPDATE tasks SET status = 'planned', assigned_to = NULL, assigned_at = NULL, "
            "lease_expires_at = NULL, assignment_reason = NULL, result = NULL, result_at = NULL, "
            "tokens_per_second = NULL, files = NULL, validation_status = 'pending', "
            "validation_message = NULL WHERE id = ?",
            (task_id,),
        )
        return "requeued"


def release_all_ready_tasks() -> int:
    """Flip blocked tasks to planned when all their dependencies are done (DAG scheduler)."""
    with _connect() as conn:
        blocked = conn.execute("SELECT id FROM tasks WHERE status = 'blocked'").fetchall()
        released = 0
        for row in blocked:
            task_id = row[0]
            deps = conn.execute(
                "SELECT dep.status FROM task_dependencies td "
                "JOIN tasks dep ON dep.id = td.depends_on_task_id "
                "WHERE td.task_id = ?",
                (task_id,),
            ).fetchall()
            if all(d[0] == "done" for d in deps):
                conn.execute("UPDATE tasks SET status = 'planned' WHERE id = ?", (task_id,))
                released += 1
        return released


def create_task(
    project_id: int,
    key: str,
    title: str,
    description: str,
    task_type: str,
    **options: Any,
) -> int:
    """Insert a single dynamic task (e.g. review or fix task) and return its id."""
    depends_on: list[str] | None = options.get("depends_on")
    details: dict | None = options.get("details")
    stage: int = int(options.get("stage", 2))
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (project_id, key, stage, type, title, description, details, status)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, 'planned')",
            (
                project_id, key, stage, task_type, title, description,
                json.dumps(details or {}, ensure_ascii=False),
            ),
        )
        new_id = cursor.lastrowid
        for dep_key in (depends_on or []):
            dep_row = conn.execute(
                "SELECT id FROM tasks WHERE project_id = ? AND key = ?", (project_id, dep_key)
            ).fetchone()
            if dep_row:
                conn.execute(
                    "INSERT OR IGNORE INTO task_dependencies (task_id, depends_on_task_id) VALUES (?, ?)",
                    (new_id, dep_row["id"]),
                )
    return (new_id or 0)


def list_tasks(project_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE project_id = ? ORDER BY stage, id", (project_id,)
        ).fetchall()
        deps = conn.execute(
            "SELECT t.key AS task_key, d.key AS dep_key FROM task_dependencies td "
            "JOIN tasks t ON t.id = td.task_id JOIN tasks d ON d.id = td.depends_on_task_id "
            "WHERE t.project_id = ? ORDER BY d.id",
            (project_id,),
        ).fetchall()
        conflict_rows = conn.execute(
            "SELECT task_id_a, task_id_b FROM conflicts WHERE project_id = ?", (project_id,)
        ).fetchall()
    tasks_with_conflicts: set[int] = set()
    for c in conflict_rows:
        tasks_with_conflicts.add(c["task_id_a"])
        tasks_with_conflicts.add(c["task_id_b"])
    depends_on: dict[str, list[str]] = {}
    for dep in deps:
        depends_on.setdefault(dep["task_key"], []).append(dep["dep_key"])
    result = []
    for row in rows:
        task = dict(row)
        task["details"] = json.loads(task["details"])
        task["depends_on"] = depends_on.get(task["key"], [])
        task["has_conflict"] = task["id"] in tasks_with_conflicts
        result.append(task)
    return result


def save_conflict(project_id: int, task_id_a: int, task_id_b: int, file_path: str) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO conflicts (project_id, task_id_a, task_id_b, file_path, detected_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (project_id, task_id_a, task_id_b, file_path, _utc_now()),
        )
        return cursor.lastrowid or 0


def list_conflicts(project_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM conflicts WHERE project_id = ? ORDER BY detected_at DESC",
            (project_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def resolve_conflict(conflict_id: int, resolution: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE conflicts SET resolved_at = ?, resolution = ? WHERE id = ? AND resolved_at IS NULL",
            (_utc_now(), resolution, conflict_id),
        )
        return cursor.rowcount > 0


def log_event(event_type: str, project_id: int | None = None, agent_id: str | None = None, payload: dict | None = None) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO events (project_id, agent_id, event_type, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, agent_id, event_type, json.dumps(payload, ensure_ascii=False) if payload else None, _utc_now()),
        )


def list_events(limit: int = 50, project_id: int | None = None) -> list[dict]:
    with _connect() as conn:
        if project_id is not None:
            rows = conn.execute(
                "SELECT * FROM events WHERE project_id = ? ORDER BY id DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    result = []
    for row in rows:
        e = dict(row)
        e["payload"] = json.loads(e["payload"]) if e["payload"] else None
        result.append(e)
    return result


def get_perf_stats(project_id: int | None = None) -> dict:
    """Return aggregate performance metrics for tasks."""
    with _connect() as conn:
        base = "FROM tasks WHERE perf_ms IS NOT NULL AND status = 'done'"
        params: list = []
        if project_id is not None:
            base += " AND project_id = ?"
            params.append(project_id)
        row = conn.execute(
            f"SELECT COUNT(*) as cnt, AVG(perf_ms) as avg_ms, MIN(perf_ms) as min_ms, MAX(perf_ms) as max_ms {base}",
            params,
        ).fetchone()
        by_type = conn.execute(
            f"SELECT type, COUNT(*) as cnt, AVG(perf_ms) as avg_ms {base} GROUP BY type ORDER BY avg_ms DESC",
            params,
        ).fetchall()
        by_agent = conn.execute(
            f"SELECT assigned_to, COUNT(*) as cnt, AVG(perf_ms) as avg_ms {base} GROUP BY assigned_to ORDER BY cnt DESC",
            params,
        ).fetchall()
    return {
        "total_tasks": row["cnt"] if row else 0,
        "avg_ms": round(row["avg_ms"] or 0) if row else 0,
        "min_ms": row["min_ms"] if row else None,
        "max_ms": row["max_ms"] if row else None,
        "by_type": [dict(r) for r in by_type],
        "by_agent": [dict(r) for r in by_agent],
    }
