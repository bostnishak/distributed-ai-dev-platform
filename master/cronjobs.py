"""AJN-02: cron-scheduled assistant tasks that really run.

Jobs live in the ``scheduled_tasks`` namespace of the key/value store; every execution (success or failure)
is appended to ``scheduled_runs``. The loop wakes up once a minute and runs each enabled job whose five-field
cron expression matches the current minute, at most once per minute.
"""

import asyncio
import logging
import sqlite3
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import httpx

from kvstore import PersistentDict

log = logging.getLogger(__name__)

JOBS = PersistentDict("scheduled_tasks")
RUNS = PersistentDict("scheduled_runs")

_RANGES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 6))  # minute hour day-of-month month day-of-week (0 = Sunday)
MAX_RUN_OUTPUT = 4000

Runner = Callable[[str], Awaitable[str]]


class CronError(ValueError):
    pass


def _field_values(field: str, low: int, high: int) -> set[int]:
    values: set[int] = set()
    for part in field.split(","):
        step = 1
        if "/" in part:
            part, _, step_text = part.partition("/")
            if not step_text.isdigit() or int(step_text) < 1:
                raise CronError(f"Geçersiz adım: {field}")
            step = int(step_text)
        if part in ("*", ""):
            start, end = low, high
        elif "-" in part:
            a, _, b = part.partition("-")
            if not (a.isdigit() and b.isdigit()):
                raise CronError(f"Geçersiz aralık: {field}")
            start, end = int(a), int(b)
        elif part.isdigit():
            start = end = int(part)
        else:
            raise CronError(f"Geçersiz alan: {field}")
        if start < low or end > high or start > end:
            raise CronError(f"Değer aralık dışı ({low}-{high}): {field}")
        values.update(range(start, end + 1, step))
    return values


def parse_cron(expr: str) -> list[set[int]]:
    parts = expr.split()
    if len(parts) != 5:
        raise CronError("Cron ifadesi 5 alan içermeli: dakika saat gün ay haftanın-günü")
    parsed = [_field_values(p, lo, hi) for p, (lo, hi) in zip(parts, _RANGES, strict=True)]
    if 7 in parsed[4]:  # not reachable (range is 0-6) but keep the intent explicit
        parsed[4].discard(7)
    return parsed


def cron_matches(expr: str, when: datetime) -> bool:
    minute, hour, dom, month, dow = parse_cron(expr)
    weekday = (when.weekday() + 1) % 7  # Python Monday=0 -> cron Sunday=0
    return when.minute in minute and when.hour in hour and when.day in dom and when.month in month and weekday in dow


def add_job(name: str, cron: str, prompt: str) -> dict:
    parse_cron(cron)  # raises CronError for a bad expression
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    rec = {"id": job_id, "name": name, "cron": cron, "prompt": prompt, "enabled": True, "last_run": None}
    JOBS[job_id] = rec
    return rec


def remove_job(job_id: str) -> bool:
    if job_id not in JOBS:
        return False
    del JOBS[job_id]
    return True


def recent_runs(job_id: str | None = None, limit: int = 20) -> list[dict]:
    runs = [r for r in RUNS.values() if job_id is None or r["job_id"] == job_id]
    return sorted(runs, key=lambda r: r["started_at"], reverse=True)[:limit]


async def run_due(runner: Runner, now: datetime | None = None) -> list[dict]:
    """Run every enabled job that matches ``now`` and was not already run in the same minute."""
    now = (now or datetime.now(UTC)).replace(second=0, microsecond=0)
    stamp = now.isoformat()
    done: list[dict] = []
    for job in JOBS.values():
        if not job.get("enabled") or job.get("last_run") == stamp:
            continue
        try:
            if not cron_matches(job["cron"], now):
                continue
        except CronError:
            continue
        job["last_run"] = stamp
        JOBS[job["id"]] = job
        run = {"id": f"run_{uuid.uuid4().hex[:8]}", "job_id": job["id"], "started_at": stamp, "status": "ok", "output": ""}
        try:
            run["output"] = (await runner(job["prompt"]))[:MAX_RUN_OUTPUT]
        except (
            OSError,
            RuntimeError,
            ValueError,
            TypeError,
            LookupError,
            AttributeError,
            ArithmeticError,
            ImportError,
            httpx.HTTPError,
            sqlite3.Error,
        ) as exc:
            run["status"] = "error"
            run["output"] = f"{type(exc).__name__}: {exc}"[:MAX_RUN_OUTPUT]
            log.warning("Scheduled job %s failed: %s", job["id"], exc)
        RUNS[run["id"]] = run
        done.append(run)
    return done


async def loop(runner: Runner) -> None:
    while True:
        now = datetime.now(UTC)
        await asyncio.sleep(60 - now.second - now.microsecond / 1_000_000)
        try:
            await run_due(runner)
        except Exception:
            log.exception("Scheduled job loop iteration failed")
