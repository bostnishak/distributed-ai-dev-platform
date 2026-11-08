"""Automatic review task creation after code tasks complete (PB-42, PB-43).

After a backend/frontend/database_schema/integration task is marked done,
this module creates:
  1. A sibling "review" task (reviewer != original author — PB-43).
  2. If a review task finds critical issues, a "fix" task is created (PB-42).

This is called by tasks_api after validation passes.
"""
from __future__ import annotations

import logging

import db

log = logging.getLogger(__name__)

# Task types that should automatically get a review sibling
_REVIEWABLE_TYPES = {"backend", "frontend", "database_schema", "integration"}

# Task types that should automatically get a testing sibling
_TESTABLE_TYPES = {"backend", "frontend", "integration"}


def schedule_review(completed_task: dict) -> int | None:
    """Create a review task for a completed code task.

    Returns the new task id, or None if no review was scheduled.
    """
    task_type = completed_task.get("type", "")
    if task_type not in _REVIEWABLE_TYPES:
        return None

    project_id = completed_task.get("project_id")
    performed_by = completed_task.get("performed_by")
    task_key = completed_task.get("key", "?")

    if not project_id:
        return None

    title = f"{completed_task.get('title', task_key)} — kod incelemesi"
    description = (
        f"T{completed_task.get('id', '?')} görevinin çıktısını incele. "
        "Kritik bulguları fix görevi olarak listele."
    )
    # depends_on the completed task
    depends_on = [task_key] if task_key else []

    new_id = db.create_task(
        project_id=project_id,
        key=f"{task_key}-review",
        title=title,
        description=description,
        task_type="review",
        depends_on=depends_on,
        details={"reviewed_task_id": completed_task.get("id"), "exclude_agent_id": performed_by},
    )
    log.info(
        "Created review task %d for completed task %d (project %d, exclude agent %s).",
        new_id, completed_task.get("id", -1), project_id, performed_by,
    )
    return new_id


def schedule_fix_tasks(review_task: dict, findings: list[str]) -> list[int]:
    """Create fix tasks from critical review findings (PB-42).

    Args:
        review_task: the completed review task dict.
        findings: list of critical finding strings from the review output.

    Returns:
        list of newly created fix task ids.
    """
    project_id = review_task.get("project_id")
    review_key = review_task.get("key", "?")
    if not project_id or not findings:
        return []

    new_ids = []
    for i, finding in enumerate(findings[:3], start=1):
        fix_id = db.create_task(
            project_id=project_id,
            key=f"{review_key}-fix{i}",
            title=f"Düzeltme {i}: {finding[:60]}",
            description=finding,
            task_type="backend",
            depends_on=[review_key],
            details={"fix_index": i, "source_review_task_id": review_task.get("id")},
        )
        new_ids.append(fix_id)
        log.info("Created fix task %d from review %d finding %d.", fix_id, review_task.get("id", -1), i)
    return new_ids
