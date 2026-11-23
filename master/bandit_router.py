"""Cluster C ([M36]): Contextual Bandit / Thompson Sampling Router for Distributed Agents and Models."""

from __future__ import annotations

from typing import Any

from cluster_telemetry import ThompsonBanditRouter, get_local_hardware_telemetry


def select_optimal_agent_or_model(
    task_type: str,
    candidates: list[str],
    warm_models: set[str] | None = None,
    deterministic: bool = False,
) -> dict[str, Any]:
    """Convenience function selecting the highest-utility candidate via Thompson Sampling."""
    router = ThompsonBanditRouter()
    if warm_models is None:
        telemetry = get_local_hardware_telemetry(query_ollama=False)
        warm_models = set(telemetry.get("warm_models") or [])
    return router.select_best_candidate(
        task_type=task_type,
        candidates=candidates,
        warm_models=warm_models,
        deterministic=deterministic,
    )


__all__ = [
    "ThompsonBanditRouter",
    "get_local_hardware_telemetry",
    "select_optimal_agent_or_model",
]
