"""Scheduled, consistent, encrypted backups with a retention window (DAT-07).

Copying a live SQLite file together with its write-ahead log can capture a state that never existed. Each
database is therefore snapshotted with SQLite's own backup API into a staging folder first, and that folder is
what goes into the encrypted archive (backup_manager). The result is verified by restoring it into a scratch
folder before the old copies are pruned.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import backup_manager
import dbconn

SKIP_NAMES = {"backups", "scheduled", ".incoming"}
# downloaded or rebuilt on demand, so not part of a snapshot (the project folders under workspaces are kept whole)
REBUILDABLE = {"vendor", "voices", "inbox_index", "inbox_frames", "exact_cache"}
KEEP_DAILY = 7
KEEP_WEEKLY = 4


def _snapshot_databases(source: Path, staging: Path) -> None:
    for path in sorted(source.rglob("*")):
        rel = path.relative_to(source)
        if not path.is_file() or any(part in SKIP_NAMES for part in rel.parts) or rel.parts[0] in REBUILDABLE:
            continue
        target = staging / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".db":
            src = sqlite3.connect(str(path))
            try:
                dst = sqlite3.connect(str(target))
                try:
                    src.backup(dst)
                finally:
                    dst.close()
            finally:
                src.close()
        elif path.suffix not in (".db-wal", ".db-shm") and not path.name.endswith(("-wal", "-shm")):
            shutil.copy2(path, target)


def run_backup(destination: Path, password: str | None = None, data_dir: Path | None = None) -> Path:
    """Write one verified, encrypted archive into ``destination`` and return its path."""
    source = Path(data_dir) if data_dir is not None else dbconn.data_dir()
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    with tempfile.TemporaryDirectory() as staging_text, tempfile.TemporaryDirectory() as scratch_text:
        staging = Path(staging_text)
        _snapshot_databases(source, staging)
        archive = backup_manager.create_enterprise_backup_zip(data_dir=staging, password=password)
        pwd = (password or "").strip() or backup_manager._default_backup_password()
        backup_manager.restore_enterprise_backup_zip(archive, password=pwd, target_dir=Path(scratch_text))
    target = destination / f"backup-{stamp}.zip"
    target.write_bytes(archive)
    return target


def prune(destination: Path, keep_daily: int = KEEP_DAILY, keep_weekly: int = KEEP_WEEKLY) -> list[Path]:
    """Keep the newest ``keep_daily`` archives plus the newest one of each of the last ``keep_weekly`` ISO weeks."""
    archives = sorted(destination.glob("backup-*.zip"), reverse=True)
    keep = set(archives[:keep_daily])
    weeks: dict[tuple[int, int], Path] = {}
    for path in archives:
        stamp = datetime.strptime(path.stem.removeprefix("backup-")[:8], "%Y%m%d")
        iso = stamp.isocalendar()
        weeks.setdefault((iso[0], iso[1]), path)
    keep.update(list(weeks.values())[:keep_weekly])
    removed = [p for p in archives if p not in keep]
    for path in removed:
        path.unlink()
    return removed
