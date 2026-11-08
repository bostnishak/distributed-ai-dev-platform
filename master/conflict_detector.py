"""File conflict detection for completed tasks (PB-45).

When two tasks in the same project both produce a file at the same path,
that is a conflict: the second write would silently overwrite the first.
This module detects those cases after each task result is submitted.
"""

from __future__ import annotations

import json
import logging

import db

log = logging.getLogger(__name__)


def detect_and_save(project_id: int, new_task_id: int, new_files: list[dict]) -> list[dict]:
    """Compare new_task's output files against all other done tasks in the project.

    Saves any new conflicts to the database and returns them.
    new_files: list of {path, content} dicts.
    """
    if not new_files:
        return []

    new_paths = {f["path"] for f in new_files if f.get("path")}
    if not new_paths:
        return []

    # Fetch all other done tasks in this project that have files
    tasks = db.list_tasks(project_id)
    conflicts_found: list[dict] = []

    for task in tasks:
        if task["id"] == new_task_id:
            continue
        if task["status"] != "done":
            continue
        if not task.get("files"):
            continue

        try:
            existing_files = json.loads(task["files"]) if isinstance(task["files"], str) else task["files"]
        except (json.JSONDecodeError, TypeError):
            continue

        if not existing_files:
            continue

        existing_paths = {f["path"] for f in existing_files if f.get("path")}
        overlap = new_paths & existing_paths

        for path in overlap:
            conflict_id = db.save_conflict(project_id, task["id"], new_task_id, path)
            if conflict_id:
                log.warning(
                    "Conflict detected in project %d: tasks %d and %d both write '%s'",
                    project_id, task["id"], new_task_id, path,
                )
                conflicts_found.append({
                    "id": conflict_id,
                    "task_id_a": task["id"],
                    "task_id_b": new_task_id,
                    "file_path": path,
                })

    return conflicts_found
