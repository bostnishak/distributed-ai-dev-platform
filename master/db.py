"""SQLite storage for agents, projects and their task graphs.

Every call opens a short-lived connection. The data volume is small and SQLite is fast
enough for one master process, so no ORM or connection pool is needed.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime

import config

SCHEMA_VERSION = 2

# SCHEMA always describes the latest version (used for new databases). Existing databases are
# brought up to date by the statements in MIGRATIONS, keyed by the version they produce.
MIGRATIONS = {
    2: ["ALTER TABLE agents ADD COLUMN runtime TEXT"],
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS agents (
    agent_id        TEXT PRIMARY KEY,
    member_name     TEXT NOT NULL,
    model           TEXT NOT NULL,
    mode            TEXT NOT NULL,          -- 'node' (member's own computer) or 'staging'
    runtime         TEXT,                   -- 'native' or 'docker' (host values then describe the Docker VM)
    hostname        TEXT,
    os              TEXT,
    cpu_count       INTEGER,
    ram_gb          REAL,
    model_family    TEXT,
    parameter_size  TEXT,
    quantization    TEXT,
    context_length  INTEGER,
    capabilities    TEXT NOT NULL,          -- JSON array reported by Ollama, e.g. ["completion","vision"]
    agent_version   TEXT,
    registered_at   TEXT NOT NULL,          -- first registration (UTC, ISO 8601)
    last_seen_at    TEXT NOT NULL           -- latest registration; heartbeats arrive in Sprint 2
);

CREATE TABLE IF NOT EXISTS projects (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL,
    source_filename  TEXT,
    document         TEXT NOT NULL,
    status           TEXT NOT NULL,         -- analyzing | decomposed | failed
    error            TEXT,
    spec             TEXT,                  -- JSON RequirementsSpec
    analysis_model   TEXT,
    analysis_seconds REAL,
    chunk_count      INTEGER,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    key           TEXT NOT NULL,            -- T1, T2, ... (stable within a project)
    stage         INTEGER NOT NULL,         -- longest-path layer in the DAG, starting at 1
    type          TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL,
    details       TEXT NOT NULL,            -- JSON slice of the spec this task covers
    status        TEXT NOT NULL,            -- done | planned
    performed_by  TEXT,                     -- 'master' for the analysis task; agent id from Sprint 3
    UNIQUE (project_id, key)
);

CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id            INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on_task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, depends_on_task_id)
);
"""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@contextmanager
def connect():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        if row is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
            return
        version = row["version"]
        for target in sorted(MIGRATIONS):
            if target > version:
                for statement in MIGRATIONS[target]:
                    conn.execute(statement)
                version = target
        conn.execute("UPDATE schema_version SET version = ?", (version,))


# --- Agents -------------------------------------------------------------------------------

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
            assignments = ", ".join(f"{name} = :{name}" for name in AGENT_FIELDS)
            conn.execute(
                f"UPDATE agents SET {assignments}, last_seen_at = :now WHERE agent_id = :agent_id",
                {**values, "now": now, "agent_id": agent["agent_id"]},
            )
        else:
            columns = ", ".join(AGENT_FIELDS)
            placeholders = ", ".join(f":{name}" for name in AGENT_FIELDS)
            conn.execute(
                f"INSERT INTO agents (agent_id, {columns}, registered_at, last_seen_at) "
                f"VALUES (:agent_id, {placeholders}, :now, :now)",
                {**values, "now": now, "agent_id": agent["agent_id"]},
            )
    return get_agent(agent["agent_id"])


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


# --- Projects -----------------------------------------------------------------------------

def create_project(name: str, document: str, source_filename: str | None) -> int:
    now = utc_now()
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO projects (name, source_filename, document, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'analyzing', ?, ?)",
            (name, source_filename, document, now, now),
        )
        return cursor.lastrowid


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
    analysis_model: str,
    analysis_seconds: float,
    chunk_count: int,
) -> None:
    """Store the spec and the task graph in one transaction."""
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
            ids_by_key[task["key"]] = cursor.lastrowid
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


def list_tasks(project_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE project_id = ? ORDER BY stage, id", (project_id,)
        ).fetchall()
        deps = conn.execute(
            "SELECT t.key AS task_key, d.key AS dep_key FROM task_dependencies td "
            "JOIN tasks t ON t.id = td.task_id JOIN tasks d ON d.id = td.depends_on_task_id "
            "WHERE t.project_id = ? ORDER BY d.id",
            (project_id,),
        ).fetchall()
    depends_on: dict[str, list[str]] = {}
    for dep in deps:
        depends_on.setdefault(dep["task_key"], []).append(dep["dep_key"])
    result = []
    for row in rows:
        task = dict(row)
        task["details"] = json.loads(task["details"])
        task["depends_on"] = depends_on.get(task["key"], [])
        result.append(task)
    return result


def delete_project(project_id: int) -> bool:
    with connect() as conn:
        cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        return cursor.rowcount > 0
