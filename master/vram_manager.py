"""Section 5.1: Smart VRAM Budget Orchestrator & Multi-Node Model Scaling Matrix (`master/vram_manager.py`)."""

from __future__ import annotations

from typing import Any

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
    """Compute Single-Node sequential vs Multi-Node parallel execution strategy and Ollama keep_alive policy."""
    models = [m.strip() for m in (requested_models or []) if m and m.strip()]
    total_needed_gb = round(sum(estimate_model_vram_gb(m) for m in models), 2)
    agents = max(1, int(online_agents))
    vram = max(2.0, float(available_vram_gb))

    if agents >= len(models) and len(models) > 1:
        mode = "multi_node_parallel"
        keep_alive = "-1"
        fits_simultaneously = True
    elif total_needed_gb <= (vram * 0.88):
        mode = "single_node_concurrent"
        keep_alive = "10m"
        fits_simultaneously = True
    else:
        mode = "single_node_sequential"
        keep_alive = "5m"
        fits_simultaneously = False

    assignments = []
    for idx, m in enumerate(models):
        assignments.append(
            {
                "model": m,
                "estimated_vram_gb": estimate_model_vram_gb(m),
                "node_slot": f"node-{(idx % agents) + 1}",
                "keep_alive": keep_alive,
            }
        )

    return {
        "mode": mode,
        "available_vram_gb": vram,
        "online_agents": agents,
        "total_needed_vram_gb": total_needed_gb,
        "fits_simultaneously": fits_simultaneously,
        "keep_alive": keep_alive,
        "assignments": assignments,
    }
