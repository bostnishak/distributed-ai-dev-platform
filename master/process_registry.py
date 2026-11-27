"""Every long-running child is leased a port, put in a job that dies with the server, written down, and reaped.

On Windows the child joins a Job Object with kill-on-close, so killing the server (even from Task Manager) ends its
children. What escapes that (another platform, a crash before the job was set) is found at the next start from the
register: the same process (pid and creation time) whose owning server is gone gets its whole tree ended.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
from typing import Any

import psutil

import atomic_io
import config
import isolation

PORTS = range(8110, 8190)
_LOCK = threading.RLock()
_LEASED: set[int] = set()
_JOBS: dict[int, Any] = {}


def _register_file():
    return config.data_dir() / "processes.json"


def free_port(port: int) -> bool:
    """True when this process could bind it now (a connect test misses ports that are bound but not listening)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def lease_port(ports: range = PORTS) -> int:
    with _LOCK:
        for port in ports:
            if port not in _LEASED and free_port(port):
                _LEASED.add(port)
                return port
    raise OSError(f"{ports.start}-{ports.stop - 1} aralığında boş port yok")


def release_port(port: int) -> None:
    with _LOCK:
        _LEASED.discard(port)


def _load() -> list[dict[str, Any]]:
    try:
        return json.loads(atomic_io.read_text(_register_file()))
    except (OSError, ValueError):
        return []


def _save(entries: list[dict[str, Any]]) -> None:
    atomic_io.write_text(_register_file(), json.dumps(entries, ensure_ascii=False))


def _identity(pid: int) -> float:
    try:
        return round(psutil.Process(pid).create_time(), 2)
    except psutil.Error:
        return 0.0


def track(proc: subprocess.Popen, purpose: str, port: int = 0, memory_mb: int = 1024) -> None:
    """Cap the child, tie its life to ours and write it down."""
    with _LOCK:
        _JOBS[proc.pid] = isolation.contain(proc, memory_mb=memory_mb)
        entry = {"pid": proc.pid, "born": _identity(proc.pid), "owner": os.getpid(), "owner_born": _identity(os.getpid()), "purpose": purpose, "port": port}
        _save([e for e in _load() if e["pid"] != proc.pid] + [entry])


def kill_tree(pid: int, born: float) -> bool:
    """End a process and its descendants, but only if the pid still belongs to the process that was registered."""
    if not born or _identity(pid) != born:
        return False
    try:
        root = psutil.Process(pid)
        family = [*root.children(recursive=True), root]
        for member in family:
            member.kill()
        psutil.wait_procs(family, timeout=5)
    except psutil.Error:
        return False
    return True


def untrack(pid: int) -> None:
    """Stop a tracked child (closing its job ends the whole tree) and free its port."""
    with _LOCK:
        entries = _load()
        mine = next((e for e in entries if e["pid"] == pid), None)
        isolation.release(_JOBS.pop(pid, None))
        if mine:
            kill_tree(pid, mine["born"])
            release_port(mine.get("port", 0))
        _save([e for e in entries if e["pid"] != pid])


def reap() -> list[str]:
    """Forget finished children and end orphans of servers that are gone; returns what was ended."""
    ended: list[str] = []
    with _LOCK:
        keep = []
        for entry in _load():
            alive = _identity(entry["pid"]) == entry["born"] and entry["born"]
            owner_alive = _identity(entry["owner"]) == entry["owner_born"] and entry["owner_born"]
            if alive and owner_alive:
                keep.append(entry)
            elif alive and kill_tree(entry["pid"], entry["born"]):
                ended.append(f"{entry['purpose']} (pid {entry['pid']})")
        _save(keep)
    return ended


def shutdown() -> None:
    for entry in _load():
        if entry["owner"] == os.getpid():
            untrack(entry["pid"])


def listing() -> list[dict[str, Any]]:
    return [e for e in _load() if _identity(e["pid"]) == e["born"]]
