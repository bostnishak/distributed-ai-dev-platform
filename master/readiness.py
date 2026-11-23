"""Is the service ready to do work? (OPS-03)

``/health`` only says the process is alive. This module checks what the service actually needs: a writable
database, free disk, the local model server, the housekeeping loop and the code sandbox. A missing critical
piece makes the whole service "down" (HTTP 503); a missing optional one makes it "degraded".
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import config
import dbconn
import maintenance

DISK_DEGRADED_BYTES = 500 * 1024 * 1024
DISK_DOWN_BYTES = 50 * 1024 * 1024
RUNBOOKS = Path(__file__).resolve().parent.parent / "docs" / "runbooks"
_ORDER = {"ok": 0, "degraded": 1, "down": 2}


def _result(status: str, detail: str, runbook: str | None = None) -> dict:
    item = {"status": status, "detail": detail}
    if runbook and (RUNBOOKS / f"{runbook}.md").is_file():
        item["runbook"] = f"docs/runbooks/{runbook}.md"
    return item


def database() -> dict:
    started = time.perf_counter()
    try:
        conn = dbconn.open_db(config.DB_PATH)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("ROLLBACK")
        finally:
            conn.close()
    except Exception as exc:
        return _result("down", f"yazılamıyor: {exc}", "database-locked")
    return _result("ok", f"yazılabilir ({(time.perf_counter() - started) * 1000:.0f} ms)")


def disk() -> dict:
    try:
        free = shutil.disk_usage(dbconn.data_dir()).free
    except OSError as exc:
        return _result("down", f"disk okunamadı: {exc}", "disk-full")
    mb = free // (1024 * 1024)
    if free < DISK_DOWN_BYTES:
        return _result("down", f"{mb} MB boş", "disk-full")
    if free < DISK_DEGRADED_BYTES:
        return _result("degraded", f"{mb} MB boş", "disk-full")
    return _result("ok", f"{mb} MB boş")


async def ollama() -> dict:
    import llm

    try:
        state = await llm.status()
    except Exception as exc:
        return _result("degraded", f"Ollama durumu alınamadı: {exc}", "ollama-down")
    if not state.get("reachable"):
        return _result("degraded", "Ollama'ya ulaşılamıyor", "ollama-down")
    if not state.get("model_available"):
        return _result("degraded", f"{state.get('model')} modeli yüklü değil", "model-missing")
    return _result("ok", f"{state.get('model')} hazır")


def housekeeping() -> dict:
    state = maintenance.status()
    if not state["running"]:
        return _result("degraded", "bakım döngüsü çalışmıyor")
    if state["last_error"]:
        return _result("degraded", f"son tur hatalı: {state['last_error']}")
    return _result("ok", f"{state['rounds']} tur tamamlandı")


def sandbox_state() -> dict:
    try:
        import sandbox

        state = sandbox.status()
    except Exception as exc:
        return _result("degraded", f"sandbox denetlenemedi: {exc}")
    return _result("ok" if state["available"] else "degraded", state["reason"])


async def check_all() -> dict:
    components = {
        "database": database(),
        "disk": disk(),
        "ollama": await ollama(),
        "housekeeping": housekeeping(),
        "sandbox": sandbox_state(),
    }
    worst = max(components.values(), key=lambda c: _ORDER[c["status"]])["status"]
    return {"status": worst, "components": components}
