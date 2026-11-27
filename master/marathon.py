"""The fifth gear: a long build that runs in the background while the chat stays free.

  arka planda: <istek> | arka plan işleri | arka plan işini durdur <no>

The build is the ordinary one (the war room shows its agent graph and can pause or steer it), but its model calls wait
behind everything the user is doing. The job list survives a restart; a job cut off by one is marked as such.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

from fastapi.responses import StreamingResponse

import atomic_io
import config
import security_scan
from gateway import priority_gate

_log = logging.getLogger(__name__)
_START_RE = re.compile(r"^\s*(?:@marathon|arka\s*planda)\s*:\s*(?P<request>.{10,6000})$", re.IGNORECASE | re.DOTALL)
_LIST_RE = re.compile(r"^\s*arka\s*plan\s+iş(?:leri|lerim)\s*[.!?]?\s*$", re.IGNORECASE)
_STOP_RE = re.compile(r"^\s*arka\s*plan\s+işini\s+durdur\s+#?(?P<id>\d{1,6})\s*[.!]?\s*$", re.IGNORECASE)
_MAX_RUNNING = 1
_tasks: dict[int, asyncio.Task] = {}

Build = Callable[[str], AsyncIterator[dict[str, Any]]]


def _file():
    return config.data_dir() / "marathon.json"


def jobs() -> list[dict[str, Any]]:
    try:
        stored = json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    for job in stored:
        if job["state"] == "çalışıyor" and job["id"] not in _tasks:
            job["state"] = "kesildi (platform yeniden başladı)"
    return stored


def _save(job: dict[str, Any]) -> None:
    others = [j for j in jobs() if j["id"] != job["id"]]
    _file().parent.mkdir(parents=True, exist_ok=True)
    atomic_io.write_text(_file(), json.dumps(sorted([*others, job], key=lambda j: j["id"])[-30:], ensure_ascii=False, indent=1))


def _default_build(request: str) -> AsyncIterator[dict[str, Any]]:
    import project_flow

    return project_flow.stream_generate(request)


async def _run(job: dict[str, Any], request: str, build: Build) -> None:
    started = time.time()
    try:
        with priority_gate.background():  # interactive work always goes first
            async for event in build(request):
                if event.get("type") == "status":
                    job["note"] = str(event.get("message", ""))[:200]
                    _save(job)
                elif event.get("type") == "done":
                    meta = event.get("workspace") or {}
                    job.update(workspace=meta.get("id", ""), warnings=[str(w)[:200] for w in event.get("warnings", [])][:5])
        job["state"] = "bitti"
    except asyncio.CancelledError:
        job["state"] = "durduruldu"
        raise
    except Exception as exc:  # noqa: BLE001, RUF100 - whatever goes wrong must end up on the job, not vanish with the task
        _log.warning("arka plan işi %s başarısız: %r", job["id"], exc)
        job.update(state="başarısız", note=f"{type(exc).__name__}: {exc}"[:200])
    finally:
        job["seconds"] = round(time.time() - started)
        _save(job)
        _tasks.pop(job["id"], None)


def start(request: str, build: Build = _default_build) -> str:
    """Must be called inside the event loop."""
    if len(_tasks) >= _MAX_RUNNING:
        return f"Zaten çalışan bir arka plan işi var (#{next(iter(_tasks))}). Bitince ya da `arka plan işini durdur {next(iter(_tasks))}` sonrasında yenisini ver."
    number = max((j["id"] for j in jobs()), default=0) + 1
    job = {"id": number, "request": security_scan.redact(request)[:200], "state": "çalışıyor", "started": time.strftime("%Y-%m-%d %H:%M"), "note": "", "workspace": ""}
    _tasks[number] = asyncio.get_running_loop().create_task(_run(job, request, build))
    _save(job)
    return (f"**Arka plan işi #{number} başladı.** Sohbete devam edebilirsin; ilerlemeyi **Ajan grafiği**nden izleyip duraklatabilirsin.\n"
            "Durum için `arka plan işleri` yaz.")


async def stop(number: int) -> str:
    task = _tasks.get(number)
    if task is None:
        return f"#{number} numaralı çalışan bir arka plan işi yok."
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    return f"Arka plan işi #{number} durduruldu."


def listing() -> str:
    found = jobs()
    if not found:
        return "Arka plan işi yok."
    lines = [f"- #{j['id']} **{j['state']}** ({j['started']}{', ' + str(j['seconds']) + ' sn' if j.get('seconds') else ''}): {j['request'][:80]}"
             + (f" → proje `{j['workspace']}`" if j.get("workspace") else "") + (f"\n  {j['note']}" if j.get("note") and j["state"] != "bitti" else "") for j in found[-10:]]
    return "\n".join(["Arka plan işleri:", *lines])


async def reply(prompt: str, build: Build = _default_build) -> str:
    if asked := _START_RE.match(prompt):
        return start(asked["request"].strip(), build)
    if stopping := _STOP_RE.match(prompt):
        return await stop(int(stopping["id"]))
    return listing()


def fastpath(prompt: str) -> StreamingResponse | None:
    if not (_START_RE.match(prompt) or _LIST_RE.match(prompt) or _STOP_RE.match(prompt)):
        return None

    async def gen():
        yield f"data: {json.dumps({'type': 'token', 'content': await reply(prompt)}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'model': 'marathon', 'task_type': 'arka-plan'})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
