"""Point-in-time recovery from the encrypted snapshots: `ai-os backup`, `ai-os backups`, `ai-os restore <kimlik>`.

Before anything is overwritten the current state is saved as its own snapshot, so a restore can itself be undone.
After restoring, every database is checked; a damaged one is reported instead of being called restored.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import backup_manager
import backup_schedule
import config

_SETTINGS = Path(__file__).resolve().parents[1] / "ai-os.config.json"
_ID_RE = re.compile(r"^backup-(\d{8}-\d{6})(?:-[\w-]+)?\.zip$")


def folder() -> Path:
    return Path(config.DATA_DIR) / "backups"


def snapshot(label: str = "", password: str | None = None) -> str:
    """Takes a verified snapshot now; returns its id. The settings file at the top of the project travels with it."""
    if _SETTINGS.is_file():
        copy = Path(config.DATA_DIR) / "ayarlar" / _SETTINGS.name
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_SETTINGS, copy)
    archive = backup_schedule.run_backup(folder(), password=password, data_dir=Path(config.DATA_DIR))
    identifier = _ID_RE.match(archive.name).group(1)
    if label:
        archive = archive.rename(folder() / f"backup-{identifier}-{label}.zip")
    return identifier if not label else f"{identifier}-{label}"


def available() -> list[tuple[str, int]]:
    """[(id, size in bytes)] newest first."""
    found = [(p.name[len("backup-") : -len(".zip")], p.stat().st_size) for p in folder().glob("backup-*.zip") if _ID_RE.match(p.name)]
    return sorted(found, reverse=True)


def _damaged(root: Path) -> list[str]:
    broken = []
    for database in root.rglob("*.db"):
        if "backups" in database.relative_to(root).parts:
            continue
        try:
            with closing(sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)) as conn:
                if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    broken.append(database.name)
        except sqlite3.DatabaseError:
            broken.append(database.name)
    return broken


def restore(identifier: str, password: str | None = None) -> str:
    """Brings the data folder back to the snapshot; ValueError when there is no such snapshot or it does not verify."""
    archive = folder() / f"backup-{identifier}.zip"
    if not re.fullmatch(r"\d{8}-\d{6}(?:-[\w-]+)?", identifier) or not archive.is_file():
        raise ValueError(f"böyle bir yedek yok: {identifier}")
    root = Path(config.DATA_DIR)
    secret = (password or "").strip() or backup_manager._default_backup_password()
    raw = archive.read_bytes()
    undo = _safety_copy(root, identifier)
    for sidecar in [*root.rglob("*.db-wal"), *root.rglob("*.db-shm")]:
        sidecar.unlink(missing_ok=True)  # a stale write-ahead log must not be replayed over the restored database
    result = backup_manager.restore_enterprise_backup_zip(raw, password=secret, target_dir=root)
    if (saved := root / "ayarlar" / _SETTINGS.name).is_file():
        shutil.copy2(saved, _SETTINGS)
    if broken := _damaged(root):
        raise ValueError(f"geri yükleme sonrası bozuk veritabanı: {', '.join(broken)}")
    return f"{identifier} geri yüklendi ({result['restored_count']} dosya). Önceki durum: {undo}"


def _safety_copy(root: Path, identifier: str) -> str:
    """The databases and small state as they are now (a corrupt file is copied as it is, not re-read)."""
    target = folder() / f"onceki-{identifier}"
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_file() and relative.parts[0] not in backup_schedule.SKIP_NAMES and path.stat().st_size < 20_000_000:
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    return str(target)
