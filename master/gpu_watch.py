"""Watch the one graphics card: temperature, memory used by others, battery; hold background work when it is not safe.

Interactive requests are never refused. Background jobs (practice, benchmarks, inbox) wait while the card is at or
above the temperature ceiling or the machine runs on a low battery, and the context size asked from the model is
reduced when something else has taken most of the card's memory.
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass

import psutil

import process_utils

CEILING_C = int(os.environ.get("GPU_TEMP_CEILING", "82"))
_RESUME_MARGIN = 4
_CACHE_S = 5.0
_CACHE: dict[str, object] = {"at": 0.0, "value": None, "holding": False}


@dataclass(frozen=True)
class Reading:
    temperature: int
    used_mb: int
    total_mb: int
    source: str


def _from_nvml() -> Reading | None:
    try:
        import pynvml  # provided by nvidia-ml-py
    except ImportError:
        return None
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return Reading(int(pynvml.nvmlDeviceGetTemperature(handle, 0)), memory.used // 2**20, memory.total // 2**20, "nvml")
    except pynvml.NVMLError:
        return None


def _from_smi() -> Reading | None:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    done = process_utils.run_process([exe, "--query-gpu=temperature.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"], timeout_s=10)
    try:
        temperature, used, total = (int(x) for x in done.stdout.splitlines()[0].split(","))
    except (IndexError, ValueError):
        return None
    return Reading(temperature, used, total, "nvidia-smi")


def read() -> Reading | None:
    """The latest reading (cached for a few seconds); None on a machine without an NVIDIA card."""
    if time.monotonic() - float(_CACHE["at"]) > _CACHE_S:
        _CACHE.update(at=time.monotonic(), value=_from_nvml() or _from_smi())
    return _CACHE["value"]


def on_low_battery() -> bool:
    battery = psutil.sensors_battery()
    return bool(battery and not battery.power_plugged and battery.percent < 50)


def hold_reason() -> str:
    """Why background work should wait now ('' when it may run). Cooling needs a few degrees below the ceiling."""
    reading = read()
    if reading:
        limit = CEILING_C - _RESUME_MARGIN if _CACHE["holding"] else CEILING_C
        _CACHE["holding"] = reading.temperature >= limit
        if _CACHE["holding"]:
            return f"ekran kartı {reading.temperature} °C (sınır {CEILING_C} °C)"
    return "pil düşük" if on_low_battery() else ""


def context_budget(requested: int, loaded_mb: int = 0) -> int:
    """num_ctx to ask for: smaller when other programs left less memory than a model needs."""
    reading = read()
    if not reading or not reading.total_mb:
        return requested
    free = reading.total_mb - max(0, reading.used_mb - loaded_mb)
    if free < 2500:
        return min(requested, 4096)
    return min(requested, 8192) if free < 4500 else requested


def summary() -> str:
    reading = read()
    if not reading:
        return "Ekran kartı okunamadı."
    held = hold_reason()
    return (f"Ekran kartı: {reading.temperature} °C, {reading.used_mb / 1024:.1f} / {reading.total_mb / 1024:.1f} GB ({reading.source})."
            + (f" Arka plan işleri bekliyor: {held}." if held else " Arka plan işleri serbest."))
