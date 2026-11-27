"""Isolation tiers that work on Windows besides Docker.

`run_capped` puts a process in a Job Object (memory and process limits, everything dies with the job): the fallback when
Docker is stopped. `run_wasm` executes WebAssembly with no file or network access and a fuel limit.
"""

from __future__ import annotations

import ctypes
import subprocess
import sys
from ctypes import wintypes

_SUSPENDED = 0x4
_KILL_ON_CLOSE, _ACTIVE_PROCESS, _JOB_MEMORY, _EXTENDED_LIMITS = 0x2000, 0x8, 0x200, 9


class _Basic(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64), ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]


class _Extended(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _Basic), ("IoInfo", ctypes.c_uint64 * 6), ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


def _job(memory_mb: int, processes: int) -> tuple[ctypes.WinDLL, int]:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    handle = kernel.CreateJobObjectW(None, None)
    limits = _Extended()
    limits.BasicLimitInformation.LimitFlags = _KILL_ON_CLOSE | _ACTIVE_PROCESS | _JOB_MEMORY
    limits.BasicLimitInformation.ActiveProcessLimit = processes
    limits.JobMemoryLimit = memory_mb * 1024 * 1024
    if not handle or not kernel.SetInformationJobObject(handle, _EXTENDED_LIMITS, ctypes.byref(limits), ctypes.sizeof(limits)):
        raise OSError(ctypes.get_last_error(), "iş nesnesi kurulamadı")
    return kernel, handle


def tie(proc: subprocess.Popen) -> tuple[ctypes.WinDLL, int] | None:
    """A job without resource limits: closing it ends the process and everything it started. None where unavailable."""
    if sys.platform != "win32":
        return None
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateJobObjectW(None, None)
    limits = _Extended()
    limits.BasicLimitInformation.LimitFlags = _KILL_ON_CLOSE
    if handle and kernel.SetInformationJobObject(handle, _EXTENDED_LIMITS, ctypes.byref(limits), ctypes.sizeof(limits)) and kernel.AssignProcessToJobObject(handle, int(proc._handle)):
        return kernel, handle
    if handle:
        kernel.CloseHandle(handle)
    return None


def run_capped(args: list[str], memory_mb: int = 512, processes: int = 8, timeout_s: float = 30.0) -> subprocess.CompletedProcess:
    """Run with hard limits and a minimal environment (Windows only; raises OSError elsewhere)."""
    if sys.platform != "win32":
        raise OSError("Job Object yalnızca Windows'ta var")
    kernel, handle = _job(memory_mb, processes)
    env = {"SYSTEMROOT": "C:\\Windows", "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, creationflags=_SUSPENDED) as proc:  # noqa: S603, RUF100
            if not kernel.AssignProcessToJobObject(handle, int(proc._handle)):
                proc.kill()
                raise OSError(ctypes.get_last_error(), "süreç iş nesnesine alınamadı")
            resume = ctypes.WinDLL("ntdll").NtResumeProcess  # started suspended so no work happens outside the limits
            resume.argtypes = [wintypes.HANDLE]
            resume(int(proc._handle))
            try:
                out, err = proc.communicate(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                kernel.TerminateJobObject(handle, 1)  # kills every process of the job and reports failure
                out, err = proc.communicate()
            return subprocess.CompletedProcess(args, proc.returncode, out, err)
    finally:
        if handle:
            kernel.CloseHandle(handle)


def contain(proc: subprocess.Popen, memory_mb: int = 1024, processes: int = 16) -> tuple[ctypes.WinDLL, int] | None:
    """Put an already started long-running process under memory and process limits; None where that is not possible.

    Closing the returned handle (`release`) ends the whole process tree.
    """
    if sys.platform != "win32":
        return None
    try:
        kernel, handle = _job(memory_mb, processes)
    except OSError:
        return None
    if not kernel.AssignProcessToJobObject(handle, int(proc._handle)):
        kernel.CloseHandle(handle)
        return None
    return kernel, handle


def release(contained: tuple[ctypes.WinDLL, int] | None) -> None:
    if contained:
        contained[0].CloseHandle(contained[1])


def run_wasm(wat_or_wasm: str | bytes, function: str, *values: int, fuel: int = 1_000_000) -> int:
    """Call an exported function with no imports (no files, no network); RuntimeError when it runs out of fuel or traps."""
    import wasmtime

    config = wasmtime.Config()
    config.consume_fuel = True
    engine = wasmtime.Engine(config)
    store = wasmtime.Store(engine)
    store.set_fuel(fuel)
    try:
        instance = wasmtime.Instance(store, wasmtime.Module(engine, wat_or_wasm), [])
        return instance.exports(store)[function](store, *values)
    except (wasmtime.WasmtimeError, wasmtime.Trap, KeyError) as exc:
        raise RuntimeError(str(exc).splitlines()[0]) from exc
