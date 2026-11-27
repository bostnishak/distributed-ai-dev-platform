"""What the server does for the operating system when it starts, stops, and when the machine wakes from sleep."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import re
import sys
import time
from typing import Any

import db_health
import disk_gc
import gpu_watch
import process_registry

log = logging.getLogger(__name__)
_ASK_RE = re.compile(r"^\s*(?:sistem\s+durumu|system\s+status)\s*\??\s*$", re.IGNORECASE)
_TICK_S = 15.0
STATE: dict[str, Any] = {"broken_databases": {}, "reaped": [], "wakes": 0, "started": 0.0}


def force_utf8() -> None:
    """Children inherit UTF-8, and our own console never falls back to the old Turkish code page."""
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper) and stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")


def startup() -> dict[str, Any]:
    force_utf8()
    STATE.update(reaped=process_registry.reap(), broken_databases=db_health.startup_check(), started=time.time())
    if STATE["reaped"]:
        log.warning("önceki oturumdan kalan süreçler kapatıldı: %s", STATE["reaped"])
    for name, problem in STATE["broken_databases"].items():
        log.error("veritabanı sağlam değil: %s: %s", name, problem)
    return STATE


def shutdown() -> None:
    process_registry.shutdown()
    db_health.flush()


def woke_from_sleep(elapsed: float, expected: float = _TICK_S) -> bool:
    """The clock jumped far beyond the pause we asked for: the machine slept or hibernated."""
    return elapsed > expected + 60


async def watch_sleep() -> None:
    previous = time.time()
    while True:
        await asyncio.sleep(_TICK_S)
        now = time.time()
        if woke_from_sleep(now - previous):
            STATE["wakes"] += 1
            log.info("uyku sonrası toparlanma: süreçler ve veritabanları denetleniyor")
            STATE["reaped"] = await asyncio.to_thread(process_registry.reap)
            await asyncio.to_thread(db_health.flush)
        previous = now


def status() -> str:
    children = process_registry.listing()
    broken = STATE["broken_databases"]
    lines = [gpu_watch.summary(), disk_gc.status(),
             f"Veritabanları: {'sorunlu: ' + ', '.join(broken) if broken else f'{len(db_health.databases())} dosya, açılış denetimi temiz'}",
             f"Çalışan alt süreç: {len(children)}" + "".join(f"\n- {c['purpose']} (pid {c['pid']}, port {c['port'] or '-'})" for c in children[:8]),
             f"Bu oturumda kapatılan yetim süreç: {len(STATE['reaped'])}, uyku sonrası toparlanma: {STATE['wakes']}"]
    return "\n".join(lines)


def answer(prompt: str) -> str:
    return status() if _ASK_RE.match(prompt) else disk_gc.answer(prompt)
