"""Heavy parts run only while they are needed: start on first use, release after DAEMON_IDLE_TTL idle seconds.

In-process engines (speech, transcription) register how to drop themselves; the local search container is started
when a search needs it and stopped again only if this process started it. Browser, solver, spreadsheet and sandbox
runs already end with their task, and vision models are unloaded after each answer.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterator

import httpx

import process_utils

SEARCH_CONTAINER = "dadp-searxng-json"
_LIVE: dict[str, tuple[float, Callable[[], None]]] = {}
_LOCK = threading.Lock()
_STATE: dict[str, threading.Thread | None] = {"reaper": None}
_BUSY: Counter = Counter()
SEARCH = "yerel arama (SearXNG)"
_COMMAND_RE = re.compile(r"^\s*(?:servis(?:ler(?:in)?)?\s+durumu|service\s+status)\s*\??\s*$", re.IGNORECASE)


def idle_ttl() -> float:
    return max(5.0, float(os.environ.get("DAEMON_IDLE_TTL", "120")))


def touch(name: str, stop: Callable[[], None]) -> None:
    """Mark an engine as used now; `stop` is called once it has been idle long enough."""
    with _LOCK:
        _LIVE[name] = (time.monotonic(), stop)
        if _STATE["reaper"] is None or not _STATE["reaper"].is_alive():
            _STATE["reaper"] = threading.Thread(target=_reap_forever, name="daemon-reaper", daemon=True)
            _STATE["reaper"].start()


@contextlib.contextmanager
def in_use(name: str) -> Iterator[None]:
    """An engine is never stopped while a request is using it; its idle time starts when the last one finishes."""
    with _LOCK:
        _BUSY[name] += 1
    try:
        yield
    finally:
        with _LOCK:
            _BUSY[name] -= 1
            if name in _LIVE:
                _LIVE[name] = (time.monotonic(), _LIVE[name][1])


def reap(now: float | None = None) -> list[str]:
    """Stop everything idle longer than the limit; returns the names stopped."""
    current = time.monotonic() if now is None else now
    with _LOCK:
        due = [(name, stop) for name, (used, stop) in _LIVE.items() if not _BUSY[name] and current - used >= idle_ttl()]
        for name, _stop in due:
            del _LIVE[name]
    for _name, stop in due:
        stop()
    return [name for name, _stop in due]


def _reap_forever() -> None:
    while _LIVE:
        time.sleep(min(15.0, idle_ttl() / 2))
        reap()


def _docker(*args: str) -> process_utils.ProcessResult | None:
    exe = shutil.which("docker")
    if not exe:
        return None
    try:
        return process_utils.run_process([exe, *args], timeout_s=40)
    except (OSError, subprocess.SubprocessError):
        return None


def _container_state() -> str:
    done = _docker("inspect", "-f", "{{.State.Status}}", SEARCH_CONTAINER)
    return done.stdout.strip() if done and done.returncode == 0 else ""


def _answers(url: str) -> bool:
    try:
        return httpx.get(url, timeout=3).status_code < 500
    except httpx.HTTPError:
        return False


def ensure_search(url: str) -> bool:
    """True when the local search answers; a stopped search container is started first and stopped again when idle."""
    if _answers(url):
        if SEARCH in _LIVE:
            touch(SEARCH, _stop_search)
        return True
    if _container_state() not in ("exited", "created"):
        return False
    done = _docker("start", SEARCH_CONTAINER)
    if not done or done.returncode != 0:
        return False
    touch(SEARCH, _stop_search)
    for _ in range(30):
        if _answers(url):
            return True
        time.sleep(1)
    return False


def _stop_search() -> None:
    _docker("stop", SEARCH_CONTAINER)


def status() -> str:
    now = time.monotonic()
    with _LOCK:
        live = [(name, int(now - used)) for name, (used, _stop) in _LIVE.items()]
    lines = [f"Boşta kalan ağır parçalar {int(idle_ttl())} sn sonra kapatılır."]
    lines += [f"- {name}: açık, {idle} sn'dir boşta" for name, idle in live] or ["- Bu süreçte açık ağır parça yok (0 MB)."]
    state = _container_state()
    lines.append(f"- Yerel arama kabı: {'çalışıyor' if state == 'running' else 'kapalı, ilk aramada açılır' if state else 'kurulu değil'}")
    lines.append("- Tarayıcı, Z3, kod kutusu: her iş sonunda kapanır. Görsel modeli: her yanıttan sonra bellekten atılır.")
    return "\n".join(lines)


def answer(prompt: str) -> str:
    return status() if _COMMAND_RE.match(prompt) else ""
