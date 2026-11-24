"""Background housekeeping: retention, blob and event cleanup, WAL checkpoint, scheduled backup.

One supervised thread runs ``run_once`` on an interval. If a round raises, the error is logged and counted and
the loop carries on (with a growing pause), so a bug in one job cannot silently stop housekeeping for good.
``status()`` reports the last round for the readiness check (OPS-03).
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from datetime import UTC, datetime

import backup_schedule
import blobstore
import config
import dbconn
import events_log
import retention

log = logging.getLogger(__name__)

_state: dict = {"last_run": None, "last_error": None, "rounds": 0, "failures": 0}
_stop = threading.Event()
_RUNTIME: dict[str, threading.Thread | None] = {"thread": None}
_lock = threading.Lock()


def run_once() -> dict:
    report: dict = {}
    with dbconn.connection(config.DB_PATH) as conn:
        report["retention"] = retention.purge_expired(conn)
        report["blobs"] = blobstore.collect_garbage(conn)
        report["events_pruned"] = events_log.prune(conn)
    checkpoint = sqlite3.connect(str(config.DB_PATH))
    try:
        checkpoint.execute("PRAGMA wal_checkpoint(PASSIVE)")
    finally:
        checkpoint.close()
    hours = float(getattr(config, "BACKUP_INTERVAL_HOURS", 0) or 0)
    if hours > 0:
        folder = dbconn.data_dir() / "backups" / "scheduled"
        newest = max(folder.glob("backup-*.zip"), default=None, key=lambda p: p.stat().st_mtime) if folder.is_dir() else None
        if newest is None or time.time() - newest.stat().st_mtime >= hours * 3600:
            report["backup"] = backup_schedule.run_backup(folder, password=config.BACKUP_PASSWORD or None).name
            report["backups_pruned"] = len(backup_schedule.prune(folder))
    with _lock:
        _state["last_run"] = datetime.now(UTC).isoformat(timespec="seconds")
        _state["rounds"] += 1
    return report


def status() -> dict:
    with _lock:
        thread = _RUNTIME["thread"]
        return {**_state, "running": bool(thread and thread.is_alive())}


def _loop(interval: float) -> None:
    pause = interval
    while not _stop.is_set():
        try:
            run_once()
            pause = interval
        except Exception as exc:
            log.exception("bakım turu başarısız")
            with _lock:
                _state["failures"] += 1
                _state["last_error"] = f"{type(exc).__name__}: {exc}"
            pause = min(pause * 2, 3600)
        _stop.wait(pause)


def start_background(interval_seconds: float = 3600) -> None:
    thread = _RUNTIME["thread"]
    if thread and thread.is_alive():
        return
    _stop.clear()
    new_thread = threading.Thread(target=_loop, args=(interval_seconds,), name="maintenance", daemon=True)
    _RUNTIME["thread"] = new_thread
    new_thread.start()


def stop_background(timeout: float = 5.0) -> None:
    _stop.set()
    thread = _RUNTIME["thread"]
    if thread:
        thread.join(timeout)

