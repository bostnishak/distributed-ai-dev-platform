"""OPS-24: Resource & Energy Management (Idle Model Unload Policy + Battery Power Profile Advisor)."""

from __future__ import annotations

import time
from typing import Any

IDLE_UNLOAD_SECONDS = 600.0  # 10 minutes default


class PowerManager:
    """Tracks per-model last-used timestamps to recommend idle unloading and battery-safe smaller models."""

    def __init__(self, *, idle_unload_seconds: float = IDLE_UNLOAD_SECONDS) -> None:
        self.idle_unload_seconds = float(idle_unload_seconds)
        self._last_used: dict[str, float] = {}

    def touch(self, model: str, *, now: float | None = None) -> None:
        self._last_used[model] = time.monotonic() if now is None else float(now)

    def models_due_for_unload(self, *, now: float | None = None) -> list[str]:
        cur = time.monotonic() if now is None else float(now)
        return sorted(m for m, ts in self._last_used.items() if (cur - ts) >= self.idle_unload_seconds)

    @staticmethod
    def recommend_for_power_profile(requested_model: str, *, on_battery: bool, battery_pct: int = 100) -> dict[str, Any]:
        if on_battery and battery_pct <= 40 and any(sz in requested_model.lower() for sz in ("9b", "14b", "32b", "70b")):
            return {
                "recommended_model": "qwen3.5:4b",
                "downgraded": True,
                "reason": f"Pil modu (%{battery_pct}): enerji ve ısı koruması için küçük model önerildi.",
            }
        return {"recommended_model": requested_model, "downgraded": False, "reason": "Standart güç profili."}
