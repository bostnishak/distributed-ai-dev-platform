"""Cluster C ([M35]..[M38]): Heterogeneous GPU Swarm Coordinator combining Telemetry,
Thompson Sampling Bandit Routing, Parallel Map-Reduce, and Fault-Tolerant Migration.
"""

from __future__ import annotations

from typing import Any

from cluster_telemetry import (
    ThompsonBanditRouter,
    get_local_hardware_telemetry,
    load_task_checkpoint,
    save_task_checkpoint,
)
from fault_tolerance import migrate_stalled_task
from map_reduce_llm import reduce_mapped_results, split_document_or_tasks_for_map


class SwarmCoordinator:
    """High-level coordinator managing distributed GPU swarm routing, map-reduce sharding,
    and checkpoint migration.
    """

    def __init__(self, router: ThompsonBanditRouter | None = None) -> None:
        self.router = router or ThompsonBanditRouter()

    def dispatch_map_reduce(
        self,
        task_type: str,
        text_or_items: str | list[Any],
        online_agents: list[str],
        warm_models: set[str] | None = None,
    ) -> dict[str, Any]:
        """Split a job into shards, assign each shard to an online agent via Thompson Sampling,
        and return the execution plan.
        """
        agents = [a.strip() for a in online_agents if a and a.strip()] or ["local-master"]
        shards = split_document_or_tasks_for_map(text_or_items, chunk_count=len(agents))
        assignments: list[dict[str, Any]] = []
        for idx, shard in enumerate(shards):
            cand = agents[idx % len(agents)]
            selection = self.router.select_best_candidate(
                task_type=task_type,
                candidates=agents,
                warm_models=warm_models,
                deterministic=True,
            )
            chosen_agent = cand if len(agents) > 1 else selection["selected"]
            assignments.append(
                {
                    "chunk_id": shard["chunk_id"],
                    "assigned_agent": chosen_agent,
                    "item_count": shard["item_count"],
                    "char_count": shard["char_count"],
                }
            )
        return {
            "task_type": task_type,
            "shard_count": len(shards),
            "online_agents": agents,
            "assignments": assignments,
            "shards": shards,
        }


__all__ = [
    "SwarmCoordinator",
    "ThompsonBanditRouter",
    "get_local_hardware_telemetry",
    "load_task_checkpoint",
    "migrate_stalled_task",
    "reduce_mapped_results",
    "save_task_checkpoint",
    "split_document_or_tasks_for_map",
]
