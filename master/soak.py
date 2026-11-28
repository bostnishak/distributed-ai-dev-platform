"""Burn-in: a real server is worked for hours with mixed tasks and injected faults while its resources are watched.

  python scripts/ai_os.py soak --hours 4          (add --no-model to leave the graphics card alone)

Sampled: resident memory of the server and its children, open handles, child processes, listening ports, video memory,
data folder size. It fails on memory that keeps growing, processes or ports left behind after the stop, SQLite lock
errors, out-of-memory errors and unanswered requests.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import random
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx
import psutil

import gpu_watch
from gateway import providers

_APP_DIR = Path(__file__).resolve().parent
_BAD_LOG = ("database is locked", "out of memory", "CUDA error", "MemoryError")
_GROWTH_LIMIT = 0.30  # resident memory may not end more than this above where it settled after warm-up
_WARMUP_SHARE = 0.25
_SAMPLE_S = 15.0
_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Sample:
    at: float
    rss_mb: float
    handles: int
    children: int
    ports: int
    vram_mb: int
    disk_mb: float


@dataclass
class Run:
    base: str
    data: Path
    model: bool
    done: dict[str, int] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    samples: list[Sample] = field(default_factory=list)


def _get(run: Run, path: str) -> None:
    httpx.get(run.base + path, timeout=60).raise_for_status()


def _chat(run: Run, prompt: str) -> str:
    text = []
    with httpx.stream("POST", f"{run.base}/api/assistant/chat/stream", files={"prompt": (None, prompt)}, timeout=900) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                if event.get("type") == "error":
                    raise RuntimeError(str(event.get("content"))[:200])
                text.append(str(event.get("content") or ""))
    return "".join(text)


def _expect(condition: bool, problem: str) -> None:
    if not condition:
        raise RuntimeError(problem)


def _gear0(run: Run) -> None:
    a, b = random.randint(100, 999), random.randint(100, 999)  # noqa: S311, RUF100  # workload variety, not security
    _expect(str(a * b) in _chat(run, f"{a} * {b} kaç eder?").replace(".", ""), "hesap yanlış")


def _status(run: Run) -> None:
    for path in ("/health", "/api/glass/hardware", "/api/glass/unfinished"):
        _get(run, path)


def _report(run: Run) -> None:
    _expect("son haneye kadar" in _chat(run, f"tutarlı rapor: yük {random.randint(1, 999999)}; koli {random.randint(2, 90)} x 4,50; bant 3 x 12,75"), "rapor doğrulanmadı")  # noqa: S311, RUF100


def _inbox(run: Run) -> None:
    _expect("nbox" in _chat(run, "inbox"), "inbox yanıtlamadı")


def _hostile(run: Run) -> None:
    """Fault injection: nonsense, oversized and abandoned requests must be refused, never crash the server."""
    _expect(httpx.post(f"{run.base}/api/assistant/chat/stream", content=os.urandom(2048), headers={"content-type": "multipart/form-data; boundary=x"}, timeout=60).status_code < 500, "bozuk istek sunucu hatası verdi")
    _expect(httpx.get(f"{run.base}/api/glass/proof/..%2F..", timeout=30).status_code in (400, 404), "yol kaçışı reddedilmedi")
    try:  # a client that hangs up in the middle of a stream
        with httpx.stream("POST", f"{run.base}/api/assistant/chat/stream", files={"prompt": (None, "12 * 12 kaç eder?")}, timeout=60) as response:
            next(response.iter_bytes(), None)
    except httpx.HTTPError:
        pass


def _short_answer(run: Run) -> None:
    _expect(len(_chat(run, "SQLite WAL modunu iki cümleyle anlat.")) > 40, "yanıt boş")


def _swap(run: Run) -> None:
    """A second model family takes the card and is then released."""
    del run
    asyncio.run(providers.load_and_release("llama3.2:3b"))


CPU_TASKS: dict[str, Callable[[Run], None]] = {"hesap (GEAR_0)": _gear0, "durum": _status, "dörtlü rapor": _report, "inbox": _inbox, "arıza enjeksiyonu": _hostile}
MODEL_TASKS: dict[str, Callable[[Run], None]] = {"kısa yanıt (GEAR_1)": _short_answer, "model değişimi": _swap}


def _tree(process: psutil.Process) -> list[psutil.Process]:
    try:
        return [process, *process.children(recursive=True)]
    except psutil.NoSuchProcess:
        return []


def sample(run: Run, process: psutil.Process, started: float) -> Sample:
    members = _tree(process)
    rss = handles = ports = 0
    for member in members:
        try:
            rss += member.memory_info().rss
            handles += member.num_handles() if hasattr(member, "num_handles") else member.num_fds()
            ports += sum(c.status == psutil.CONN_LISTEN for c in member.net_connections())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    card = gpu_watch.read()
    disk = sum(p.stat().st_size for p in run.data.rglob("*") if p.is_file())
    return Sample(round(time.time() - started, 1), round(rss / 2**20, 1), handles, max(0, len(members) - 1), ports, card.used_mb if card else 0, round(disk / 2**20, 2))


def growth(samples: list[Sample]) -> float:
    """How far the typical memory of the last quarter is above that of the first quarter after warm-up."""
    settled = samples[int(len(samples) * _WARMUP_SHARE) :]
    quarter = max(1, len(settled) // 4)
    early = statistics.median(s.rss_mb for s in settled[:quarter])
    late = statistics.median(s.rss_mb for s in settled[-quarter:])
    return (late - early) / early if early else 0.0


def verdict(run: Run, log_text: str, leftovers: list[str]) -> list[str]:
    problems = [f"günlükte '{word}'" for word in _BAD_LOG if word.lower() in log_text.lower()]
    problems += run.failures[:5]
    if len(run.samples) >= 8 and (rise := growth(run.samples)) > _GROWTH_LIMIT:
        problems.append(f"bellek sürekli büyüyor: %{rise * 100:.0f}")
    return problems + leftovers


def _port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _boot(folder: Path, log: Any) -> tuple[subprocess.Popen, str, list[int]]:
    port, preview = _port(), _port()
    env = {**os.environ, "DB_PATH": str(folder / "data" / "platform.db"), "WORKSPACES_DIR": str(folder / "data" / "workspaces"), "PREVIEW_PORT": str(preview), "PYTHONIOENCODING": "utf-8"}
    server = subprocess.Popen([sys.executable, "-X", "utf8", "-m", "uvicorn", "app:app", "--app-dir", str(_APP_DIR), "--host", "127.0.0.1", "--port", str(port)],  # noqa: S603, RUF100
                              cwd=_APP_DIR, env=env, stdout=log, stderr=log)
    base = f"http://127.0.0.1:{port}"
    for _ in range(120):
        time.sleep(0.5)
        try:
            if httpx.get(f"{base}/health", timeout=2).status_code == 200:
                return server, base, [port, preview]
        except httpx.HTTPError:
            continue
    server.kill()
    raise RuntimeError("sunucu açılmadı")


def _stop(server: subprocess.Popen, ports: list[int]) -> list[str]:
    """Stops the server; whatever is still running or listening afterwards is a leak."""
    members = _tree(psutil.Process(server.pid))
    for member in members:
        try:
            member.terminate()
        except psutil.NoSuchProcess:
            continue
    _gone, alive = psutil.wait_procs(members, timeout=20)
    leftovers = [f"artık süreç: {p.pid}" for p in alive]
    for port in ports:
        with socket.socket() as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                leftovers.append(f"açık kalan port: {port}")
    return leftovers


@contextlib.contextmanager
def _watching(run: Run, process: psutil.Process, every: float):
    """Samples on its own thread, so a slow task never leaves a gap in the measurements."""
    started, stop = time.time(), threading.Event()

    def loop() -> None:
        while True:
            run.samples.append(sample(run, process, started))
            if stop.wait(every):
                break

    watcher = threading.Thread(target=loop, daemon=True)
    watcher.start()
    try:
        yield
    finally:
        stop.set()
        watcher.join(timeout=60)
        run.samples.append(sample(run, process, started))


def _work(run: Run, seconds: float) -> None:
    tasks = {**CPU_TASKS, **(MODEL_TASKS if run.model else {})}
    names, started = list(tasks), time.time()
    turn = 0
    while time.time() - started < seconds or turn < len(names):  # every kind of task runs at least once
        name = names[turn % len(names)]
        turn += 1
        if name in MODEL_TASKS and (reason := gpu_watch.hold_reason()):
            _log.warning("model işi bekletildi: %s", reason)
            time.sleep(5)
            continue
        try:
            tasks[name](run)
            run.done[name] = run.done.get(name, 0) + 1
        except (httpx.HTTPError, RuntimeError, ValueError, OSError) as exc:
            run.failures.append(f"{name}: {type(exc).__name__}: {str(exc)[:160]}")
        time.sleep(0.5)


def soak(hours: float, *, model: bool = True, out: Path | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="cm6453_soak_", ignore_cleanup_errors=True) as tmp:
        folder = Path(tmp)
        log_path = folder / "server.log"
        with log_path.open("w", encoding="utf-8") as log:
            server, base, ports = _boot(folder, log)
            run = Run(base, folder / "data", model)
            try:
                with _watching(run, psutil.Process(server.pid), min(_SAMPLE_S, hours * 3600 / 20)):
                    _work(run, hours * 3600)
            finally:
                leftovers = _stop(server, ports)
        problems = verdict(run, log_path.read_text(encoding="utf-8", errors="replace"), leftovers)
    report = {"hours": hours, "model": model, "tasks": run.done, "failures": run.failures[:30], "problems": problems,
              "memory_growth": round(growth(run.samples), 3) if len(run.samples) >= 8 else None,
              "peak_rss_mb": max(s.rss_mb for s in run.samples), "peak_vram_mb": max(s.vram_mb for s in run.samples), "samples": [asdict(s) for s in run.samples]}
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return report
