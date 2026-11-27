"""Keep a generated web server running for the user, in the same locked-down container the delivery proof uses.

"sunucuyu başlat" opens it on a local port, "sunucuyu durdur" removes it, "sunucu durumu" lists what runs. The
watchdog asks `check()` on every tick; a server that stopped on its own is recorded in the project's history.
"""

from __future__ import annotations

import atexit
import contextlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import event_log
import live_server

_log = logging.getLogger(__name__)
_ASK_RE = re.compile(r"^\s*(?:proje\s+)?sunucu(?:sunu|yu)?\s+(?P<what>başlat|durdur|durumu)\s*[.!?]?\s*$", re.IGNORECASE)
_MAX_RUNNING = 3


@dataclass
class _Running:
    ws_dir: Path
    server: live_server.LiveServer
    holder: contextlib.AbstractContextManager[Any]


_running: dict[str, _Running] = {}


def start(ws_dir: Path) -> str:
    """The URL of the project's server; OSError or ValueError says why it could not be opened."""
    ws_id = ws_dir.name
    if ws_id in _running and _running[ws_id].server.alive():
        return _running[ws_id].server.url
    stop(ws_id)
    while len(_running) >= _MAX_RUNNING:
        stop(next(iter(_running)))
    holder = live_server.serve(ws_dir)
    server = holder.__enter__()
    _running[ws_id] = _Running(ws_dir, server, holder)
    event_log.record(ws_dir, "sunucu başladı", server.url)
    return server.url


def stop(ws_id: str) -> bool:
    entry = _running.pop(ws_id, None)
    if entry is None:
        return False
    try:
        entry.holder.__exit__(None, None, None)
    except (OSError, RuntimeError) as exc:
        _log.warning("proje sunucusu kaldırılamadı: %r", exc)
    return True


def stop_all() -> None:
    for ws_id in list(_running):
        stop(ws_id)


atexit.register(stop_all)


def check() -> list[str]:
    """Workspace ids whose server stopped on its own since the last look."""
    dead = []
    for ws_id, entry in list(_running.items()):
        if entry.server.alive():
            continue
        reason = entry.server.reason()
        event_log.record(entry.ws_dir, "sunucu durdu", reason)
        _log.warning("proje sunucusu durdu: %s (%s)", ws_id, reason)
        stop(ws_id)
        dead.append(ws_id)
    return dead


def answer(prompt: str, ws_dir: Path | None) -> str:
    """The reply to a server command; "" when the message is something else."""
    asked = _ASK_RE.match(prompt)
    if asked is None:
        return ""
    what = asked["what"].lower()
    if what == "durumu":
        lines = [f"- {ws_id}: {e.server.url} ({'çalışıyor' if e.server.alive() else 'durmuş'})" for ws_id, e in _running.items()]
        return "\n".join(["Çalışan proje sunucuları:", *lines]) if lines else "Çalışan proje sunucusu yok."
    if ws_dir is None or not ws_dir.is_dir():
        return "Bu sohbette bir proje yok. Önce bir FastAPI ya da Flask projesi oluştur."
    if what == "durdur":
        return "Proje sunucusu durduruldu." if stop(ws_dir.name) else "Bu projenin çalışan bir sunucusu yok."
    try:
        url = start(ws_dir)
    except (OSError, ValueError) as exc:
        return f"Sunucu açılamadı: {exc}"
    return (f"Proje sunucusu çalışıyor: {url}\n\nYalıtılmış kutuda projenin bir **kopyası** çalışıyor; orada girdiğin veriler proje "
            "dosyalarına yazılmaz. Kapatmak için: `sunucuyu durdur`.")
