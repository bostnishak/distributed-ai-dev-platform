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


MODEL_VRAM_GB: dict[str, float] = {
    "bge-m3:latest": 1.2,
    "qwen3:1.7b": 1.4,
    "llama3.2:3b": 2.2,
    "phi4-mini": 2.6,
    "qwen3.5:4b": 3.3,
    "gemma4:e4b": 4.2,
    "qwen2.5-coder:7b": 4.7,
    "cnc-ballooner": 5.2,
    "qwen3.5:9b": 6.6,
    "qwen2.5-coder:32b": 19.5,
    "deepseek-r1:32b": 20.0,
}


def estimate_model_vram_gb(model_name: str) -> float:
    norm = (model_name or "").strip().lower()
    if norm in MODEL_VRAM_GB:
        return MODEL_VRAM_GB[norm]
    for key, gb in MODEL_VRAM_GB.items():
        if key.split(":")[0] in norm:
            return gb
    return 4.5


def compute_vram_execution_plan(
    requested_models: list[str],
    available_vram_gb: float = 8.0,
    online_agents: int = 1,
) -> dict[str, Any]:
    """GW-06 / OPS-24: Single-node sequential vs multi-node parallel VRAM plan & Ollama keep_alive policy."""
    models = [m.strip() for m in (requested_models or []) if m and m.strip()]
    total_needed_gb = round(sum(estimate_model_vram_gb(m) for m in models), 2)
    agents = max(1, online_agents)
    vram = max(2.0, float(available_vram_gb))

    if agents >= len(models) and len(models) > 1:
        mode, keep_alive, fits = "multi_node_parallel", "-1", True
    elif total_needed_gb <= (vram * 0.88):
        mode, keep_alive, fits = "single_node_concurrent", "10m", True
    else:
        mode, keep_alive, fits = "single_node_sequential", "5m", False

    assignments = [
        {"model": m, "estimated_vram_gb": estimate_model_vram_gb(m), "node_slot": f"node-{(i % agents) + 1}", "keep_alive": keep_alive}
        for i, m in enumerate(models)
    ]
    return {
        "mode": mode,
        "available_vram_gb": vram,
        "online_agents": agents,
        "total_needed_vram_gb": total_needed_gb,
        "fits_simultaneously": fits,
        "keep_alive": keep_alive,
        "assignments": assignments,
    }
