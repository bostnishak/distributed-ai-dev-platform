"""Background care when the machine is idle: notice a project server that died, and measure quality at night.

A dead live server is written to the project's event log with its exit code. With SELF_EVAL_HOUR set, the golden
benchmark runs once a day at that hour while nobody is using the models, with prompt rollback on regression.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import external_watch
import memory_conflicts
import memory_engine
import memory_maintenance
import night_summary
import process_registry
import project_server
import self_play
from process_utils import spawn_process

_log = logging.getLogger(__name__)
_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "golden.py"
_state: dict[str, str] = {"last_eval_day": "", "last_play_day": ""}


def check_servers() -> list[str]:
    """Workspace ids whose live server stopped on its own since the last look."""
    return project_server.check()


def nightly_due(now: time.struct_time, hour: str, idle: Callable[[], bool]) -> bool:
    day = time.strftime("%Y-%m-%d", now)
    return hour.isdigit() and now.tm_hour == int(hour) and _state["last_eval_day"] != day and idle()


def consolidate_memory() -> int:
    """Merge repeated learned facts and queue contradictions for the user, for every user with stored facts."""
    owners = sorted({str(f.get("user_id", "default")) for f in memory_engine.list_semantic_facts()} | {"default"})
    merged = 0
    for owner in owners:
        try:
            with memory_conflicts._connect() as conn:
                merged += int(memory_maintenance.consolidate(conn, owner).get("merged", 0))
        except (sqlite3.Error, ValueError, AttributeError) as exc:
            _log.warning("bellek birleştirme başarısız (%s): %s", owner, exc)
    return merged


def play_due(now: time.struct_time, hour: str, idle: Callable[[], bool]) -> bool:
    return hour.isdigit() and now.tm_hour == int(hour) and _state["last_play_day"] != time.strftime("%Y-%m-%d", now) and idle()


def tick(idle: Callable[[], bool], now: time.struct_time | None = None) -> None:
    check_servers()
    external_watch.scan()
    now = now or time.localtime()
    if nightly_due(now, os.environ.get("SELF_EVAL_HOUR", ""), idle) and _SCRIPT.is_file():
        _state["last_eval_day"] = time.strftime("%Y-%m-%d", now)
        consolidate_memory()
        _log.info("günlük özet: %s", night_summary.write())
        process_registry.track(spawn_process([sys.executable, str(_SCRIPT), "--auto-rollback"], cwd=_SCRIPT.parent.parent), "gece kalite ölçümü", memory_mb=4096)
        _log.info("gece kalite ölçümü başlatıldı")
    if play_due(now, os.environ.get("SELF_PLAY_HOUR", ""), idle):
        _state["last_play_day"] = time.strftime("%Y-%m-%d", now)
        threading.Thread(target=self_play.run_idle, args=(idle,), name="self-play", daemon=True).start()
        _log.info("boşta alıştırma başlatıldı")
