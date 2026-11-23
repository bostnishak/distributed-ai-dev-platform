"""Versioned SQL migrations (DAT-02).

Files named ``NNNN_name.sql`` in a directory are applied once, in order, each inside one transaction, and
recorded in ``schema_migrations`` with a checksum. Editing a migration that already ran is an error: add a new
file instead. Before anything is applied to a database that already holds data, a snapshot is written so a
failed upgrade can be undone by copying it back.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import dbconn

FILE_NAME = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")
SNAPSHOTS_KEPT = 5


class MigrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path
    checksum: str

    @property
    def sql(self) -> str:
        return self.path.read_text(encoding="utf-8")


def discover(directory: Path) -> list[Migration]:
    found: list[Migration] = []
    for path in sorted(directory.glob("*.sql")):
        match = FILE_NAME.match(path.name)
        if match is None:
            raise MigrationError(f"{path.name}: dosya adı 'NNNN_ad.sql' biçiminde olmalı")
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        found.append(Migration(int(match.group(1)), match.group(2), path, checksum))
    versions = [m.version for m in found]
    if len(set(versions)) != len(versions):
        raise MigrationError(f"yinelenen sürüm numarası: {sorted(v for v in versions if versions.count(v) > 1)}")
    return found


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version INTEGER PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)"
    )


def applied(conn: sqlite3.Connection) -> dict[int, tuple[str, str]]:
    _ensure_table(conn)
    return {r[0]: (r[1], r[2]) for r in conn.execute("SELECT version, name, checksum FROM schema_migrations")}


def pending(conn: sqlite3.Connection, directory: Path) -> list[Migration]:
    done = applied(conn)
    todo: list[Migration] = []
    for migration in discover(directory):
        if migration.version in done:
            if done[migration.version][1] != migration.checksum:
                raise MigrationError(
                    f"{migration.path.name}: uygulanmış göç sonradan değiştirilmiş; yeni bir göç dosyası ekleyin"
                )
        else:
            todo.append(migration)
    if todo and done and todo[0].version < max(done):
        raise MigrationError(f"{todo[0].path.name}: daha yüksek sürümler zaten uygulanmış (sıra bozuk)")
    return todo


def snapshot(db_path: Path, directory: Path) -> Path | None:
    """Copy the database (consistently, via SQLite's backup API) before upgrading; keep only the newest few."""
    if not db_path.is_file() or db_path.stat().st_size == 0:
        return None
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    target = directory / f"pre-migrate-{db_path.stem}-{stamp}.db"
    source = sqlite3.connect(str(db_path))
    try:
        dest = sqlite3.connect(str(target))
        try:
            source.backup(dest)
        finally:
            dest.close()
    finally:
        source.close()
    old = sorted(directory.glob(f"pre-migrate-{db_path.stem}-*.db"))
    for stale in old[:-SNAPSHOTS_KEPT]:
        stale.unlink(missing_ok=True)
    return target


def apply_pending(
    db_path: Path | str, directory: Path, *, snapshot_dir: Path | None = None, dry_run: bool = False
) -> list[str]:
    """Apply every pending migration; returns their file names. All-or-nothing per file."""
    db_path = Path(db_path)
    probe = dbconn.open_db(db_path)
    try:
        todo = pending(probe, directory)
    finally:
        probe.close()
    if not todo or dry_run:
        return [m.path.name for m in todo]
    if snapshot_dir is not None:
        snapshot(db_path, snapshot_dir)
    conn = dbconn.open_db(db_path)
    conn.isolation_level = None
    try:
        for migration in todo:
            stamp = datetime.now(UTC).isoformat(timespec="seconds")
            script = (
                "BEGIN IMMEDIATE;\n"
                + migration.sql
                + "\n;INSERT INTO schema_migrations (version, name, checksum, applied_at) VALUES "
                + f"({migration.version}, '{migration.name}', '{migration.checksum}', '{stamp}');\nCOMMIT;"
            )
            try:
                conn.executescript(script)
            except sqlite3.Error as exc:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise MigrationError(f"{migration.path.name}: {exc}") from exc
    finally:
        conn.close()
    return [m.path.name for m in todo]
