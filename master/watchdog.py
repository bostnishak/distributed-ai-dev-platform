"""Background care when the machine is idle: notice a project server that died, and measure quality at night.

A dead live server is written to the project's event log with its exit code. With SELF_EVAL_HOUR set, the golden
benchmark runs once a day at that hour while nobody is using the models, with prompt rollback on regression.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

import event_log
import workspace_builder_ops as ops
from process_utils import spawn_process

_log = logging.getLogger(__name__)
_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "golden.py"
_state: dict[str, str] = {"last_eval_day": ""}


def check_servers() -> list[str]:
    """Workspace ids whose live server stopped on its own since the last look."""
    dead = []
    for ws_id, (_port, proc) in list(ops._RUNNING_SERVERS.items()):
        code = proc.poll()
        if code is None:
            continue
        ops._RUNNING_SERVERS.pop(ws_id, None)
        try:
            event_log.record(ops.safe_workspace_dir(ws_id), "sunucu durdu", f"çıkış kodu {code}")
        except ValueError:
            _log.warning("watchdog: bilinmeyen çalışma alanı %s", ws_id)
        _log.warning("proje sunucusu durdu: %s (çıkış kodu %s)", ws_id, code)
        dead.append(ws_id)
    return dead


def nightly_due(now: time.struct_time, hour: str, idle: Callable[[], bool]) -> bool:
    day = time.strftime("%Y-%m-%d", now)
    return hour.isdigit() and now.tm_hour == int(hour) and _state["last_eval_day"] != day and idle()


def tick(idle: Callable[[], bool], now: time.struct_time | None = None) -> None:
    check_servers()
    now = now or time.localtime()
    if nightly_due(now, os.environ.get("SELF_EVAL_HOUR", ""), idle) and _SCRIPT.is_file():
        _state["last_eval_day"] = time.strftime("%Y-%m-%d", now)
        spawn_process([sys.executable, str(_SCRIPT), "--auto-rollback"], cwd=_SCRIPT.parent.parent)
        _log.info("gece kalite ölçümü başlatıldı")
