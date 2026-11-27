"""One way to open a SQLite file (DAT-03) and one place to decide where a module's tables live (DAT-01).

Every module used to call ``sqlite3.connect`` with its own settings; only one enabled WAL, none set a busy
timeout, so a background thread writing while a request read could raise "database is locked".
"""

from __future__ import annotations

import re
import sqlite3
import threading
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import config

BUSY_TIMEOUT_MS = 10_000


_WRITE_RE = re.compile(r"^\s*(?:insert|update|delete|replace|create|alter|drop|begin|vacuum|reindex)\b", re.IGNORECASE)
_writers: dict[str, threading.RLock] = {}
_writers_guard = threading.Lock()


def writer_lock(path: Path | str) -> threading.RLock:
    key = str(Path(path).resolve()).casefold()
    with _writers_guard:
        return _writers.setdefault(key, threading.RLock())


class SerialConnection(sqlite3.Connection):
    """Writes to one database file queue up here instead of colliding inside SQLite.

    The first writing statement takes the file's lock; commit, rollback or close gives it back. Waiting is bounded by
    the busy timeout, after which SQLite's own locking decides, so a forgotten transaction can never hang the platform.
    """

    lock: threading.RLock | None = None
    held = False

    def _queue(self, statement: str) -> None:
        if self.lock is not None and not self.held and _WRITE_RE.match(statement):
            self.held = self.lock.acquire(timeout=BUSY_TIMEOUT_MS / 1000)

    def _done(self) -> None:
        if self.held and not self.in_transaction:
            self.held = False
            self.lock.release()

    def execute(self, sql, *args):
        self._queue(sql)
        try:
            return super().execute(sql, *args)
        finally:
            self._done()

    def executemany(self, sql, *args):
        self._queue(sql)
        try:
            return super().executemany(sql, *args)
        finally:
            self._done()

    def executescript(self, script):
        self._queue("begin")
        try:
            return super().executescript(script)
        finally:
            self._done()

    def commit(self):
        try:
            super().commit()
        finally:
            self._done()

    def rollback(self):
        try:
            super().rollback()
        finally:
            self._done()

    def close(self):
        try:
            super().close()
        finally:
            if self.held:
                self.held = False
                self.lock.release()


class ClosingConnection(SerialConnection):
    """``with conn:`` commits or rolls back like the standard class, then closes.

    The standard ``with sqlite3.connect(...)`` leaves the connection open until it is garbage collected; on
    Windows that keeps the database file locked and undeletable.
    """

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()  # close() also gives the write lock back


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
    conn.lock = writer_lock(target)
    if row_factory:
        conn.row_factory = sqlite3.Row
    return configure(conn)


@contextmanager
def connection(path: Path | str) -> Generator[sqlite3.Connection, None, None]:
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
