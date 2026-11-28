"""Snapshot and burn-in commands in the chat.

  yedek al                takes a verified, encrypted snapshot now
  yedekler                lists the snapshots; restoring needs the server stopped: python scripts/ai_os.py restore <kimlik>
  dayanıklılık raporu     the result of the last `python scripts/ai_os.py soak --hours N`
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi.responses import StreamingResponse

import recovery
import soak

_REPORT = Path(__file__).resolve().parents[1] / "eval" / "reports" / "soak.json"
_COMMAND_RE = re.compile(r"^\s*(?P<what>yedek\s+al|yedekler|dayanıklılık\s+raporu)\s*[.!]?\s*$", re.IGNORECASE)


def _snapshots() -> str:
    found = recovery.available()
    if not found:
        return "Henüz yedek yok. `yedek al` yazabilirsin."
    listed = "\n".join(f"- `{name}` ({size / 2**20:.1f} MB)" for name, size in found[:15])
    return f"{listed}\n\nGeri yüklemek için sunucuyu durdurup: `python scripts/ai_os.py restore <kimlik>`"


def _burn_in() -> str:
    try:
        report = json.loads(_REPORT.read_text(encoding="utf-8"))
        done = sum(report["tasks"].values())
        verdict = "TEMİZ" if not report["problems"] else "SORUNLU: " + "; ".join(report["problems"][:4])
        return f"Son yakma testi: {report['hours']:g} saat, {done} iş, {len(soak.CPU_TASKS) + (len(soak.MODEL_TASKS) if report['model'] else 0)} iş türü, en yüksek bellek {report['peak_rss_mb']} MB. {verdict}"
    except (OSError, ValueError, KeyError):
        return "Kayıtlı yakma testi yok. Çalıştırmak için: `python scripts/ai_os.py soak --hours 4`"


def answer(prompt: str) -> str:
    """The reply to one of the commands; "" for everything else."""
    match = _COMMAND_RE.match(prompt)
    if not match:
        return ""
    what = " ".join(match["what"].lower().split())
    if what == "yedek al":
        return f"Yedek alındı ve doğrulandı: `{recovery.snapshot()}`"
    return _snapshots() if what == "yedekler" else _burn_in()


async def _stream(prompt: str) -> AsyncIterator[str]:
    import assistant_stream_fastpaths as fp

    try:
        yield fp.sse_event({"type": "token", "content": await asyncio.to_thread(answer, prompt)})
        yield fp.sse_event({"type": "done", "model": "bakim", "task_type": "bakim"})
    except (OSError, ValueError, RuntimeError) as exc:
        yield fp.sse_event({"type": "error", "content": f"Yedek işlemi yapılamadı: {exc}"})


def fastpath(prompt: str) -> StreamingResponse | None:
    return StreamingResponse(_stream(prompt), media_type="text/event-stream") if _COMMAND_RE.match(prompt) else None
