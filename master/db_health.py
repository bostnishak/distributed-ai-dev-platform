"""Keep the SQLite files trustworthy: check them at start, copy them safely before changes, flush them at stop."""

from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from pathlib import Path

import config
import dbconn

_KEEP_BACKUPS = 5


def databases() -> list[Path]:
    folder = config.data_dir()
    return sorted(p for p in folder.glob("*.db") if p.is_file())


def quick_check(path: Path) -> str:
    """'ok' or the first problem SQLite reports."""
    try:
        with closing(sqlite3.connect(path, timeout=dbconn.BUSY_TIMEOUT_MS / 1000)) as conn:
            return str(conn.execute("PRAGMA quick_check(1)").fetchone()[0])
    except sqlite3.DatabaseError as exc:
        return str(exc)


def hot_backup(path: Path, label: str = "manual") -> Path:
    """A consistent copy taken while the database is in use (SQLite's online backup), keeping the newest few."""
    folder = config.data_dir() / "backups" / "db"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = time.time_ns()  # sorts by age and never repeats, even for copies taken in the same second
    target = folder / f"{path.stem}-{label}-{time.strftime('%Y%m%d-%H%M%S')}-{stamp}.db"
    while target.exists():  # the Windows clock ticks coarsely
        stamp += 1
        target = target.with_name(f"{path.stem}-{label}-{time.strftime('%Y%m%d-%H%M%S')}-{stamp}.db")
    with closing(sqlite3.connect(path, timeout=dbconn.BUSY_TIMEOUT_MS / 1000)) as source, closing(sqlite3.connect(target)) as copy:
        source.backup(copy)
    for old in sorted(folder.glob(f"{path.stem}-{label}-*.db"), reverse=True)[_KEEP_BACKUPS:]:
        old.unlink(missing_ok=True)
    return target


def startup_check() -> dict[str, str]:
    """{file name: problem} for databases that fail the check; healthy ones are copied once per start."""
    broken: dict[str, str] = {}
    for path in databases():
        result = quick_check(path)
        if result != "ok":
            broken[path.name] = result
        elif path == Path(config.DB_PATH).resolve():
            hot_backup(path, "boot")
    return broken


def flush() -> int:
    """Move each write-ahead log into its database (before sleep, reboot or stop); returns files flushed."""
    done = 0
    for path in databases():
        try:
            with closing(sqlite3.connect(path, timeout=dbconn.BUSY_TIMEOUT_MS / 1000)) as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            done += 1
        except sqlite3.DatabaseError:
            continue
    return done
