"""One way to open a SQLite file (DAT-03) and one place to decide where a module's tables live (DAT-01).

Every module used to call ``sqlite3.connect`` with its own settings; only one enabled WAL, none set a busy
timeout, so a background thread writing while a request read could raise "database is locked".
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import config

BUSY_TIMEOUT_MS = 10_000


class ClosingConnection(sqlite3.Connection):
    """``with conn:`` commits or rolls back like the standard class, then closes.

    The standard ``with sqlite3.connect(...)`` leaves the connection open until it is garbage collected; on
    Windows that keeps the database file locked and undeletable.
    """

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def configure(conn: sqlite3.Connection) -> sqlite3.Connection:
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA synchronous = NORMAL")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.OperationalError:
        pass  # in-memory and read-only databases cannot switch journal mode
    return conn


def open_db(path: Path | str, *, row_factory: bool = True) -> sqlite3.Connection:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=BUSY_TIMEOUT_MS / 1000, factory=ClosingConnection)
    if row_factory:
        conn.row_factory = sqlite3.Row
    return configure(conn)


@contextmanager
def connection(path: Path | str) -> Iterator[sqlite3.Connection]:
    """Commit on success, roll back on error, always close (unlike ``with sqlite3.connect``)."""
    conn = open_db(path)
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def data_dir() -> Path:
    return Path(getattr(config, "DATA_DIR", Path(config.DB_PATH).parent))


def database_file(legacy_name: str) -> Path:
    """Where a module keeps its tables: ``platform.db`` when UNIFIED_DB is on, else its own legacy file."""
    if getattr(config, "UNIFIED_DB", False):
        return Path(config.DB_PATH)
    return data_dir() / legacy_name
