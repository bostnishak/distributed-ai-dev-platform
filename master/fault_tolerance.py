"""Cluster C ([M38]): Step-Level Task Checkpointing and Fault-Tolerant Agent Task Migration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cluster_telemetry import load_task_checkpoint, save_task_checkpoint


def migrate_stalled_task(task_id: str, new_agent_id: str) -> dict[str, Any]:
    """Migrate a stalled or disconnected task from its latest persisted checkpoint to ``new_agent_id``."""
    target_agent = (new_agent_id or "").strip()
    if not target_agent:
        raise ValueError("new_agent_id must not be empty")

    existing = load_task_checkpoint(task_id)
    now_iso = datetime.now(UTC).isoformat()

    if existing is None:
        initial_state: dict[str, Any] = {
            "assigned_agent": target_agent,
            "previous_agent": None,
            "migration_count": 1,
            "migrated_at": now_iso,
            "resumed_from_step": 0,
        }
        saved = save_task_checkpoint(task_id=task_id, step=0, state=initial_state)
        return {
            "task_id": saved["task_id"],
            "migrated": True,
            "had_existing_checkpoint": False,
            "resumed_step": 0,
            "previous_agent": None,
            "new_agent_id": target_agent,
            "migration_count": 1,
            "state": saved["state"],
        }

    step_num = int(existing.get("step", 0))
    state = dict(existing.get("state") or {})
    prev_agent = state.get("assigned_agent") or state.get("agent_id")
    migration_count = int(state.get("migration_count", 0)) + 1

    state["previous_agent"] = prev_agent
    state["assigned_agent"] = target_agent
    state["migration_count"] = migration_count
    state["migrated_at"] = now_iso
    state["resumed_from_step"] = step_num

    saved = save_task_checkpoint(task_id=task_id, step=step_num, state=state)
    return {
        "task_id": saved["task_id"],
        "migrated": True,
        "had_existing_checkpoint": True,
        "resumed_step": step_num,
        "previous_agent": prev_agent,
        "new_agent_id": target_agent,
        "migration_count": migration_count,
        "state": saved["state"],
    }


__all__ = [
    "load_task_checkpoint",
    "migrate_stalled_task",
    "save_task_checkpoint",
]
