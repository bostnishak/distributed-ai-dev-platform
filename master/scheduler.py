"""DAG scheduler: releases blocked tasks when all their dependencies are done (PB-34).

After a task is marked done, call release_after_completion() immediately; the background
loop is a safety net that catches any tasks the synchronous call may have missed (e.g. after
a restart).
"""

import asyncio
import logging
import sqlite3
from typing import Any

import db

log = logging.getLogger("scheduler")
_STATE: dict[str, Any] = {"running": False, "dag_task": None}


def release_after_completion(completed_task_id: int) -> int:
    """Called synchronously after a task result is saved. Returns number of tasks released."""
    released = db.release_all_ready_tasks()
    if released:
        log.info("DAG: %d task(s) released after task %d completed.", released, completed_task_id)
    return released


async def _dag_loop() -> None:
    if _STATE["running"]:
        return
    _STATE["running"] = True
    while True:
        try:
            released = db.release_all_ready_tasks()
            if released:
                log.info("DAG scheduler background pass: released %d task(s).", released)
        except (sqlite3.Error, OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
            log.warning("DAG scheduler error: %s", exc)
        await asyncio.sleep(60)


def start_dag_scheduler() -> None:
    _STATE["dag_task"] = asyncio.create_task(_dag_loop())
