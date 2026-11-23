"""Cluster D ([M56]): Event-Driven & Scheduled DAG Workflow Automation Engine.

Supports ``register_workflow(name, trigger_type, trigger_config, steps)``,
``trigger_workflow(workflow_id, payload)``, and watched-folder / cron / webhook execution
with deterministic topological step ordering (Kahn's algorithm).
"""

from __future__ import annotations

import uuid
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ALLOWED_TRIGGER_TYPES = {"cron", "watched_folder", "webhook", "event", "manual"}


class AutomationEngine:
    """DAG workflow automation engine with topological step resolution and custom step handlers."""

    def __init__(self) -> None:
        self._workflows: dict[str, dict[str, Any]] = {}
        self._handlers: dict[str, Callable[[dict[str, Any], dict[str, Any]], Any]] = {}
        self._runs: list[dict[str, Any]] = []
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        self._handlers["extract"] = lambda payload, params: {
            "extracted": True,
            "source": payload.get("file") or payload.get("source") or params.get("source", "input"),
        }
        self._handlers["analyze"] = lambda payload, params: {
            "analyzed": True,
            "mode": params.get("mode", "standard"),
            "input_keys": sorted(payload.keys()),
        }
        self._handlers["archive"] = lambda payload, params: {
            "archived": True,
            "destination": params.get("destination", "archive"),
        }
        self._handlers["notify"] = lambda payload, params: {
            "notified": True,
            "channel": params.get("channel", "audit_log"),
        }

    def register_action_handler(
        self,
        action_name: str,
        handler: Callable[[dict[str, Any], dict[str, Any]], Any],
    ) -> None:
        """Register a custom callable for step ``action`` execution."""
        if not callable(handler):
            raise TypeError("handler must be callable")
        self._handlers[action_name.strip()] = handler

    @staticmethod
    def _topological_sort_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not steps:
            raise ValueError("Workflow must define at least one step")

        step_map: dict[str, dict[str, Any]] = {}
        indegree: dict[str, int] = {}
        dependents: dict[str, list[str]] = {}

        for idx, raw_step in enumerate(steps):
            step_id = str(raw_step.get("id") or raw_step.get("step_id") or f"step_{idx + 1}").strip()
            if step_id in step_map:
                raise ValueError(f"Duplicate step id '{step_id}' in workflow")
            deps = [str(d).strip() for d in (raw_step.get("depends_on") or []) if str(d).strip()]
            norm_step = {
                "id": step_id,
                "name": str(raw_step.get("name") or step_id),
                "action": str(raw_step.get("action") or "analyze"),
                "params": dict(raw_step.get("params") or {}),
                "depends_on": deps,
                "handler": raw_step.get("handler"),
            }
            step_map[step_id] = norm_step
            indegree[step_id] = 0
            dependents[step_id] = []

        for step_id, step in step_map.items():
            for dep in step["depends_on"]:
                if dep not in step_map:
                    raise ValueError(f"Step '{step_id}' depends on unknown step '{dep}'")
                indegree[step_id] += 1
                dependents[dep].append(step_id)

        queue: deque[str] = deque(sid for sid, deg in indegree.items() if deg == 0)
        ordered: list[dict[str, Any]] = []

        while queue:
            curr = queue.popleft()
            ordered.append(step_map[curr])
            for nxt in dependents[curr]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

        if len(ordered) != len(step_map):
            raise ValueError("Cycle detected in workflow DAG steps")

        return ordered

    def register_workflow(
        self,
        name: str,
        trigger_type: str,
        trigger_config: dict[str, Any] | None,
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Validate DAG topology and register an event-driven / scheduled workflow."""
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Workflow name cannot be empty")
        t_type = (trigger_type or "manual").strip().lower()
        if t_type not in ALLOWED_TRIGGER_TYPES:
            raise ValueError(f"Unsupported trigger_type '{trigger_type}'. Allowed: {sorted(ALLOWED_TRIGGER_TYPES)}")

        ordered_steps = self._topological_sort_steps(steps)
        wf_id = f"wf-{uuid.uuid4().hex[:10]}"

        record = {
            "workflow_id": wf_id,
            "name": clean_name,
            "trigger_type": t_type,
            "trigger_config": dict(trigger_config or {}),
            "steps": ordered_steps,
            "topological_order": [s["id"] for s in ordered_steps],
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._workflows[wf_id] = record
        return record

    def trigger_workflow(
        self,
        workflow_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a registered workflow's DAG steps in topological order."""
        if workflow_id not in self._workflows:
            raise KeyError(f"Unknown workflow_id: {workflow_id}")

        wf = self._workflows[workflow_id]
        context: dict[str, Any] = dict(payload or {})
        step_results: dict[str, Any] = {}
        executed_order: list[str] = []

        for step in wf["steps"]:
            sid = step["id"]
            action = step["action"]
            params = dict(step["params"])
            custom_callable = step.get("handler")

            if callable(custom_callable):
                output = custom_callable(context, params)
            elif action in self._handlers:
                output = self._handlers[action](context, params)
            else:
                output = {"action": action, "status": "completed", "params": params}

            step_results[sid] = output
            context[f"step_{sid}"] = output
            executed_order.append(sid)

        run_record = {
            "run_id": f"run-{uuid.uuid4().hex[:10]}",
            "workflow_id": workflow_id,
            "workflow_name": wf["name"],
            "trigger_type": wf["trigger_type"],
            "status": "COMPLETED",
            "executed_order": executed_order,
            "step_results": step_results,
            "completed_at": datetime.now(UTC).isoformat(),
        }
        self._runs.append(run_record)
        return run_record

    def poll_watched_folder(self, workflow_id: str, folder_path: Path | str | None = None) -> list[dict[str, Any]]:
        """Scan a watched folder for matching files and trigger the workflow for each file."""
        if workflow_id not in self._workflows:
            raise KeyError(f"Unknown workflow_id: {workflow_id}")
        wf = self._workflows[workflow_id]
        cfg = wf["trigger_config"]
        target_dir = Path(folder_path or cfg.get("path") or ".")
        pattern = str(cfg.get("pattern") or "*")
        if not target_dir.exists():
            return []

        runs: list[dict[str, Any]] = []
        for file_path in sorted(target_dir.glob(pattern)):
            if file_path.is_file():
                runs.append(
                    self.trigger_workflow(
                        workflow_id=workflow_id,
                        payload={"file": str(file_path), "filename": file_path.name},
                    )
                )
        return runs

    def list_workflows(self) -> list[dict[str, Any]]:
        return list(self._workflows.values())


__all__ = [
    "ALLOWED_TRIGGER_TYPES",
    "AutomationEngine",
]
