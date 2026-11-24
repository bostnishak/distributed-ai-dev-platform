"""DEF-24 & DEF-21: Safe UTF-8 subprocess helper and supervised background daemon loop."""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

_SUPERVISORS: dict[str, SupervisedLoop] = {}
_EXEC_RUN = subprocess.run
_EXEC_POPEN = subprocess.Popen


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool


def _validate_argv(cmd: list[str]) -> list[str]:
    if not isinstance(cmd, list) or not cmd or not all(isinstance(part, str) and part for part in cmd):
        raise ValueError("cmd must be a non-empty list of non-empty strings.")
    return list(cmd)


def run_process(
    cmd: list[str],
    *,
    cwd: str | os.PathLike[str] | None = None,
    timeout_s: float = 30.0,
    max_output_chars: int = 32_000,
    **options: Any,
) -> ProcessResult:
    """DEF-24: Run a subprocess with guaranteed UTF-8 decoding (never cp1254) and bounded output."""
    unknown = set(options) - {"env", "shell"}
    if unknown:
        raise TypeError(f"Unexpected keyword argument(s): {', '.join(sorted(unknown))}")
    if options.get("shell", False):
        raise ValueError("shell=True is forbidden; pass an explicit argument list.")
    argv = _validate_argv(cmd)
    env: dict[str, str] | None = options.get("env")
    merged_env = dict(os.environ if env is None else env)
    merged_env["PYTHONUTF8"] = "1"
    merged_env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = _EXEC_RUN(
            argv,
            cwd=str(cwd) if cwd is not None else None,
            env=merged_env,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
        return ProcessResult(
            returncode=proc.returncode,
            stdout=(proc.stdout or "")[-max_output_chars:],
            stderr=(proc.stderr or "")[-max_output_chars:],
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
        err = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
        return ProcessResult(
            returncode=124,
            stdout=out[-max_output_chars:],
            stderr=(err or f"Process timed out after {timeout_s}s")[-max_output_chars:],
            timed_out=True,
        )


def spawn_process(
    cmd: list[str],
    *,
    cwd: str | os.PathLike[str] | None = None,
) -> subprocess.Popen:
    """Spawn a detached non-shell child process from a strictly validated argv list."""
    argv = _validate_argv(cmd)
    return _EXEC_POPEN(
        argv,
        cwd=str(cwd) if cwd is not None else None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )


class SupervisedLoop:
    """DEF-21: Wraps a periodic background worker with exception logging, exponential backoff, and health reporting."""

    def __init__(
        self,
        name: str,
        fn: Callable[[], None],
        *,
        interval_s: float = 10.0,
        base_backoff_s: float = 0.05,
        max_backoff_s: float = 30.0,
    ) -> None:
        self.name = name
        self.fn = fn
        self.interval_s = max(0.005, float(interval_s))
        self.base_backoff_s = max(0.005, float(base_backoff_s))
        self.max_backoff_s = max(self.base_backoff_s, float(max_backoff_s))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.runs = 0
        self.restarts = 0
        self.last_ok_ts: float | None = None
        self.last_error: str = ""
        _SUPERVISORS[name] = self

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name=f"sup-{self.name}", daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 2.0) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout_s)

    def _loop(self) -> None:
        consecutive_failures = 0
        while not self._stop.is_set():
            try:
                self.fn()
                self.runs += 1
                self.last_ok_ts = time.time()
                consecutive_failures = 0
                self._stop.wait(self.interval_s)
            except Exception as exc:
                consecutive_failures += 1
                self.restarts += 1
                self.last_error = f"{type(exc).__name__}: {exc}"
                log.warning("Supervised loop '%s' crashed (restart #%d): %s", self.name, self.restarts, exc, exc_info=True)
                delay = min(self.max_backoff_s, self.base_backoff_s * (2 ** (consecutive_failures - 1)))
                self._stop.wait(delay)

    def status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "alive": bool(self._thread and self._thread.is_alive()),
            "runs": self.runs,
            "restarts": self.restarts,
            "last_ok_ts": self.last_ok_ts,
            "last_error": self.last_error,
        }


def all_supervisor_statuses() -> list[dict[str, Any]]:
    return [sup.status() for sup in _SUPERVISORS.values()]
