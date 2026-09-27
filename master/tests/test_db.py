import sqlite3

import config
import db


def test_new_database_gets_latest_version():
    db.init_db()
    with db.connect() as conn:
        assert conn.execute("SELECT version FROM schema_version").fetchone()["version"] == db.SCHEMA_VERSION
        columns = {r["name"] for r in conn.execute("PRAGMA table_info(agents)")}
    assert "runtime" in columns


def test_version_1_database_is_migrated():
    # A database created by the first Sprint 1 build: agents table without "runtime".
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.executescript(
        "CREATE TABLE schema_version (version INTEGER NOT NULL);"
        "INSERT INTO schema_version VALUES (1);"
        "CREATE TABLE agents (agent_id TEXT PRIMARY KEY, member_name TEXT NOT NULL, model TEXT NOT NULL,"
        " mode TEXT NOT NULL, hostname TEXT, os TEXT, cpu_count INTEGER, ram_gb REAL, model_family TEXT,"
        " parameter_size TEXT, quantization TEXT, context_length INTEGER, capabilities TEXT NOT NULL,"
        " agent_version TEXT, registered_at TEXT NOT NULL, last_seen_at TEXT NOT NULL);"
        "INSERT INTO agents VALUES ('uye1','İshak Bostan','qwen3.5:4b','node',NULL,NULL,NULL,NULL,NULL,"
        " NULL,NULL,NULL,'[]',NULL,'t','t');"
    )
    conn.commit()
    conn.close()

    db.init_db()
    db.init_db()  # running again must be a no-op

    agent = db.get_agent("uye1")
    assert agent["runtime"] is None
    with db.connect() as check:
        assert check.execute("SELECT version FROM schema_version").fetchone()["version"] == db.SCHEMA_VERSION
