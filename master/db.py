"""SQLite storage for agents, projects and their task graphs.

Every call opens a short-lived connection. The data volume is small and SQLite is fast
enough for one master process, so no ORM or connection pool is needed.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import config
import db_health
import db_tasks
import dbconn
import dbindexes
import dbunify
import migrate
from db_tasks import (
    MAX_ATTEMPTS,
    assign_task,
    create_task,
    expire_stale_leases,
    get_next_task_for_agent,
    get_perf_stats,
    get_task,
    list_conflicts,
    list_events,
    list_tasks,
    list_unassigned_planned_tasks,
    log_event,
    release_all_ready_tasks,
    resolve_conflict,
    save_conflict,
    submit_task_result,
    submit_task_result_with_files,
    update_task_validation,
)
from prompt_loader import load_prompt

MIGRATIONS_DIR = config.BASE_DIR / "migrations" / "platform"
SCHEMA_VERSION = 7

MIGRATIONS = {
    2: ["ALTER TABLE agents ADD COLUMN runtime TEXT"],
    3: [
        "ALTER TABLE agents ADD COLUMN heartbeat_status TEXT DEFAULT 'idle'",
        "ALTER TABLE tasks ADD COLUMN assigned_to TEXT REFERENCES agents(agent_id)",
        "ALTER TABLE tasks ADD COLUMN assigned_at TEXT",
        "ALTER TABLE tasks ADD COLUMN lease_expires_at TEXT",
        "ALTER TABLE tasks ADD COLUMN assignment_reason TEXT",
        "ALTER TABLE tasks ADD COLUMN result TEXT",
        "ALTER TABLE tasks ADD COLUMN result_at TEXT",
        "ALTER TABLE tasks ADD COLUMN tokens_per_second REAL",
        """CREATE TABLE IF NOT EXISTS eval_sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at  TEXT NOT NULL,
            finished_at TEXT,
            status      TEXT NOT NULL DEFAULT 'running'
        )""",
        """CREATE TABLE IF NOT EXISTS agent_scores (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id        TEXT NOT NULL REFERENCES agents(agent_id),
            eval_session_id INTEGER REFERENCES eval_sessions(id),
            dimension       TEXT NOT NULL,
            score           REAL NOT NULL,
            evaluated_at    TEXT NOT NULL,
            details         TEXT
        )""",
    ],
    4: [
        "ALTER TABLE tasks ADD COLUMN files TEXT",
        "ALTER TABLE tasks ADD COLUMN validation_status TEXT DEFAULT 'pending'",
        "ALTER TABLE tasks ADD COLUMN validation_message TEXT",
        "ALTER TABLE tasks ADD COLUMN attempt INTEGER DEFAULT 0",
    ],
    5: [
        """CREATE TABLE IF NOT EXISTS conflicts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            task_id_a    INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            task_id_b    INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            file_path    TEXT NOT NULL,
            detected_at  TEXT NOT NULL,
            resolved_at  TEXT,
            resolution   TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            agent_id    TEXT REFERENCES agents(agent_id) ON DELETE SET NULL,
            event_type  TEXT NOT NULL,
            payload     TEXT,
            created_at  TEXT NOT NULL
        )""",
    ],
    6: [
        "ALTER TABLE tasks ADD COLUMN perf_ms INTEGER",
    ],
    7: [
        "ALTER TABLE agents ADD COLUMN agent_key_hash TEXT",
        "ALTER TABLE agents ADD COLUMN agent_key_revoked INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE agents ADD COLUMN approved INTEGER NOT NULL DEFAULT 1",
    ],
}

SCHEMA = load_prompt("b4_db_schema.txt")

__all__ = [
    "AGENT_FIELDS",
    "MAX_ATTEMPTS",
    "MIGRATIONS",
    "MIGRATIONS_DIR",
    "SCHEMA",
    "SCHEMA_VERSION",
    "apply_sql_migrations",
    "assign_task",
    "connect",
    "create_eval_session",
    "create_project",
    "create_task",
    "delete_project",
    "expire_stale_leases",
    "fail_interrupted_analyses",
    "finish_eval_session",
    "get_agent",
    "get_agent_scores",
    "get_next_task_for_agent",
    "get_perf_stats",
    "get_project",
    "get_task",
    "init_db",
    "list_agents",
    "list_conflicts",
    "list_events",
    "list_projects",
    "list_tasks",
    "list_unassigned_planned_tasks",
    "log_event",
    "mark_analyzing",
    "mark_failed",
    "release_all_ready_tasks",
    "requeue_task",
    "resolve_conflict",
    "save_agent_score",
    "save_conflict",
    "save_decomposition",
    "submit_task_result",
    "submit_task_result_with_files",
    "update_heartbeat",
    "update_task_validation",
    "upsert_agent",
    "utc_now",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@contextmanager
def connect():
    conn = dbconn.open_db(config.DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def apply_sql_migrations() -> list[str]:
    """DAT-02: numbered SQL files on top of the legacy in-code schema (version 7 is the baseline)."""
    return migrate.apply_pending(config.DB_PATH, MIGRATIONS_DIR, snapshot_dir=dbconn.data_dir() / "backups")


def init_db() -> None:
    if getattr(config, "UNIFIED_DB", False):
        dbunify.unify(dbconn.data_dir(), Path(config.DB_PATH))
    with connect() as conn:
        conn.executescript(SCHEMA)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        if row is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        else:
            version = row["version"]
            if any(target > version for target in MIGRATIONS):
                db_health.hot_backup(Path(config.DB_PATH), "gecis")  # a copy before the schema changes
            for target in sorted(MIGRATIONS):
                if target > version:
                    for statement in MIGRATIONS[target]:
                        try:
                            conn.execute(statement)
                        except sqlite3.OperationalError as exc:
                            if "duplicate column name" not in str(exc).lower():
                                raise
                    version = target
            conn.execute("UPDATE schema_version SET version = ?", (version,))
    apply_sql_migrations()
    with connect() as conn:
        dbindexes.ensure_indexes(conn)


def requeue_task(task_id: int) -> str:
    """Reset a task to planned, or mark it permanently failed if MAX_ATTEMPTS reached."""
    return db_tasks.requeue_task(task_id, max_attempts=MAX_ATTEMPTS)


AGENT_FIELDS = (
    "member_name", "model", "mode", "runtime", "hostname", "os", "cpu_count", "ram_gb", "model_family",
    "parameter_size", "quantization", "context_length", "capabilities", "agent_version",
)


def upsert_agent(agent: dict) -> dict:
    """Insert a new agent or refresh an existing one; keeps the first registration time."""
    now = utc_now()
    values = {name: agent.get(name) for name in AGENT_FIELDS}
    values["capabilities"] = json.dumps(agent.get("capabilities") or [])
    with connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM agents WHERE agent_id = ?", (agent["agent_id"],)
        ).fetchone()
        if exists:
            conn.execute(
                "UPDATE agents SET member_name = :member_name, model = :model, mode = :mode, "
                "runtime = :runtime, hostname = :hostname, os = :os, cpu_count = :cpu_count, "
                "ram_gb = :ram_gb, model_family = :model_family, parameter_size = :parameter_size, "
                "quantization = :quantization, context_length = :context_length, "
                "capabilities = :capabilities, agent_version = :agent_version, last_seen_at = :now "
                "WHERE agent_id = :agent_id",
                {**values, "now": now, "agent_id": agent["agent_id"]},
            )
        else:
            conn.execute(
                "INSERT INTO agents (agent_id, member_name, model, mode, runtime, hostname, os, "
                "cpu_count, ram_gb, model_family, parameter_size, quantization, context_length, "
                "capabilities, agent_version, registered_at, last_seen_at) "
                "VALUES (:agent_id, :member_name, :model, :mode, :runtime, :hostname, :os, "
                ":cpu_count, :ram_gb, :model_family, :parameter_size, :quantization, :context_length, "
                ":capabilities, :agent_version, :now, :now)",
                {**values, "now": now, "agent_id": agent["agent_id"]},
            )
    rec = get_agent(agent["agent_id"])
    if rec is None:
        raise RuntimeError(f"Agent record missing after upsert: {agent['agent_id']}")
    return rec


def _agent_row(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["capabilities"] = json.loads(data["capabilities"])
    return data


def get_agent(agent_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
    return _agent_row(row) if row else None


def list_agents() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM agents ORDER BY agent_id").fetchall()
    return [_agent_row(row) for row in rows]


def update_heartbeat(agent_id: str, status: str) -> bool:
    """Update heartbeat_status and last_seen_at. Returns True if agent exists."""
    now = utc_now()
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE agents SET heartbeat_status = ?, last_seen_at = ? WHERE agent_id = ?",
            (status, now, agent_id),
        )
        return cursor.rowcount > 0


def create_eval_session() -> int:
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO eval_sessions (started_at, status) VALUES (?, 'running')",
            (utc_now(),),
        )
        return (cursor.lastrowid or 0)


def finish_eval_session(session_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE eval_sessions SET finished_at = ?, status = 'done' WHERE id = ?",
            (utc_now(), session_id),
        )


def save_agent_score(agent_id: str, eval_session_id: int, dimension: str, score: float, details: dict | None) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO agent_scores (agent_id, eval_session_id, dimension, score, evaluated_at, details) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (agent_id, eval_session_id, dimension, score, utc_now(), json.dumps(details) if details else None),
        )


def get_agent_scores(agent_id: str) -> dict:
    """Return latest score per dimension and history for an agent."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT dimension, score, evaluated_at, details FROM agent_scores "
            "WHERE agent_id = ? ORDER BY evaluated_at DESC",
            (agent_id,),
        ).fetchall()
    history = [dict(r) for r in rows]
    latest: dict[str, dict] = {}
    for r in history:
        if r["dimension"] not in latest:
            latest[r["dimension"]] = {"score": r["score"], "evaluated_at": r["evaluated_at"]}
    return {"latest": latest, "history": history}


def create_project(name: str, document: str, source_filename: str | None) -> int:
    now = utc_now()
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO projects (name, source_filename, document, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'analyzing', ?, ?)",
            (name, source_filename, document, now, now),
        )
        return (cursor.lastrowid or 0)


def get_project(project_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["spec"] = json.loads(data["spec"]) if data["spec"] else None
    return data


def list_projects() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT p.id, p.name, p.status, p.source_filename, p.analysis_seconds, "
            "p.created_at, p.updated_at, COUNT(t.id) AS task_count "
            "FROM projects p LEFT JOIN tasks t ON t.project_id = p.id "
            "GROUP BY p.id ORDER BY p.id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def mark_analyzing(project_id: int) -> None:
    """Reset a project for a new analysis run and drop its previous task graph."""
    with connect() as conn:
        conn.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
        conn.execute(
            "UPDATE projects SET status = 'analyzing', error = NULL, spec = NULL, "
            "analysis_model = NULL, analysis_seconds = NULL, chunk_count = NULL, updated_at = ? "
            "WHERE id = ?",
            (utc_now(), project_id),
        )


def mark_failed(project_id: int, error: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE projects SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
            (error, utc_now(), project_id),
        )


def fail_interrupted_analyses(message: str) -> int:
    """Projects left in 'analyzing' by a restart can never finish; mark them failed."""
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE projects SET status = 'failed', error = ?, updated_at = ? "
            "WHERE status = 'analyzing'",
            (message, utc_now()),
        )
        return cursor.rowcount


def save_decomposition(
    project_id: int,
    spec: dict,
    tasks: list[dict],
    *extra: Any,
    **meta: Any,
) -> None:
    """Store the spec and the task graph in one transaction."""
    analysis_model: str = meta.get("analysis_model", extra[0] if len(extra) > 0 else "")
    analysis_seconds: float = meta.get("analysis_seconds", extra[1] if len(extra) > 1 else 0.0)
    chunk_count: int = meta.get("chunk_count", extra[2] if len(extra) > 2 else 1)
    with connect() as conn:
        conn.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
        ids_by_key: dict[str, int] = {}
        for task in tasks:
            cursor = conn.execute(
                "INSERT INTO tasks (project_id, key, stage, type, title, description, details, "
                "status, performed_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    project_id, task["key"], task["stage"], task["type"], task["title"],
                    task["description"], json.dumps(task["details"], ensure_ascii=False),
                    task["status"], task.get("performed_by"),
                ),
            )
            ids_by_key[task["key"]] = (cursor.lastrowid or 0)
        for task in tasks:
            for dep_key in task["depends_on"]:
                conn.execute(
                    "INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES (?, ?)",
                    (ids_by_key[task["key"]], ids_by_key[dep_key]),
                )
        conn.execute(
            "UPDATE projects SET status = 'decomposed', error = NULL, spec = ?, analysis_model = ?, "
            "analysis_seconds = ?, chunk_count = ?, updated_at = ? WHERE id = ?",
            (
                json.dumps(spec, ensure_ascii=False), analysis_model, analysis_seconds,
                chunk_count, utc_now(), project_id,
            ),
        )


def delete_project(project_id: int) -> bool:
    with connect() as conn:
        cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        return cursor.rowcount > 0
