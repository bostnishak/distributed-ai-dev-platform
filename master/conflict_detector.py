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


def _parse_task_files(task: dict) -> list[dict]:
    raw_files = task.get("files")
    if not raw_files:
        return []
    try:
        parsed = json.loads(raw_files) if isinstance(raw_files, str) else raw_files
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _record_overlaps(
    project_id: int,
    existing_task_id: int,
    new_task_id: int,
    overlap: set[str],
) -> list[dict]:
    recorded: list[dict] = []
    for path in overlap:
        conflict_id = db.save_conflict(project_id, existing_task_id, new_task_id, path)
        if conflict_id:
            log.warning(
                "Conflict detected in project %d: tasks %d and %d both write '%s'",
                project_id, existing_task_id, new_task_id, path,
            )
            recorded.append({
                "id": conflict_id,
                "task_id_a": existing_task_id,
                "task_id_b": new_task_id,
                "file_path": path,
            })
    return recorded


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

    tasks = db.list_tasks(project_id)
    conflicts_found: list[dict] = []

    for task in tasks:
        if task["id"] == new_task_id or task["status"] != "done":
            continue
        existing_files = _parse_task_files(task)
        if not existing_files:
            continue
        existing_paths = {f["path"] for f in existing_files if f.get("path")}
        conflicts_found.extend(_record_overlaps(project_id, task["id"], new_task_id, new_paths & existing_paths))

    return conflicts_found
