"""Task distribution queue API.

Agents poll for their next task and submit results via these endpoints.
Both endpoints require AGENT_TOKEN.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

import conflict_detector
import db
import scheduler
import validation as val_module
from agents_api import require_agent_token
from benchmarks import BENCHMARK_BY_ID, aggregate_dimension_scores, score_response
from selection import select_agent

router = APIRouter(tags=["tasks"])
log = logging.getLogger("tasks_api")

_lease_task_running = False
_lease_task: asyncio.Task | None = None


async def _expire_leases_loop() -> None:
    global _lease_task_running
    if _lease_task_running:
        return
    _lease_task_running = True
    while True:
        try:
            expired = db.expire_stale_leases()
            if expired:
                log.info("Expired %d stale task leases.", expired)
        except Exception as exc:
            log.warning("Lease expiry error: %s", exc)
        await asyncio.sleep(60)


def start_lease_expiry() -> None:
    global _lease_task
    _lease_task = asyncio.create_task(_expire_leases_loop())


# ---------------------------------------------------------------------------
# GET /api/agents/{id}/tasks/next
# ---------------------------------------------------------------------------

@router.get("/api/agents/{agent_id}/tasks/next", dependencies=[Depends(require_agent_token)])
def next_task(agent_id: str, background_tasks: BackgroundTasks):
    """Return the next planned task assigned to this agent, or auto-assign one."""
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Ajan bulunamadı.")

    # First: check if there's already a task assigned to this agent
    task = db.get_next_task_for_agent(agent_id)
    if task:
        return task

    # Auto-assign: find an unassigned task and run selection
    unassigned = db.list_unassigned_planned_tasks()
    if not unassigned:
        return Response(status_code=204)

    # Build scores for all agents
    all_agents = db.list_agents()
    all_scores: dict[str, dict[str, float]] = {}
    for a in all_agents:
        scores_data = db.get_agent_scores(a["agent_id"])
        all_scores[a["agent_id"]] = {
            dim: info["score"] for dim, info in scores_data["latest"].items()
        }

    # Try each unassigned task until one can be assigned
    for candidate_task in unassigned:
        task_type = candidate_task.get("type", "")
        # PB-43: review tasks must not go to the task's original author
        exclude = candidate_task.get("performed_by") if task_type == "review" else None
        selected_id, reason = select_agent(
            task_type=task_type,
            task_context_tokens=0,
            available_agents=all_agents,
            all_scores=all_scores,
            exclude_agent_id=exclude,
        )
        if selected_id == agent_id:
            db.assign_task(candidate_task["id"], agent_id, reason)
            db.log_event("task_assigned", project_id=candidate_task.get("project_id"), agent_id=agent_id,
                         payload={"task_id": candidate_task["id"], "task_type": task_type})
            return db.get_task(candidate_task["id"])

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# POST /api/tasks/{id}/result
# ---------------------------------------------------------------------------

class FileResult(BaseModel):
    path: str
    content: str


class TaskResultRequest(BaseModel):
    status: str  # "done" | "failed"
    output: str
    files: list[FileResult] | None = None
    tokens_per_second: float | None = None


@router.post("/api/tasks/{task_id}/result", dependencies=[Depends(require_agent_token)])
def submit_result(task_id: int, request: TaskResultRequest):
    """Agent submits the result for a task it completed."""
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")

    files = [f.model_dump() for f in request.files] if request.files else None

    # If no explicit files, try to extract them from the output text (PB-33)
    task_type = task.get("type", "")
    if not files and request.status == "done" and task_type != "benchmark":
        files = val_module.extract_files_from_output(task_type, request.output) or None

    db.submit_task_result_with_files(
        task_id=task_id,
        status=request.status,
        output=request.output,
        files=files,
        tokens_per_second=request.tokens_per_second,
    )

    # Benchmark scoring
    if task_type == "benchmark":
        _score_benchmark_task(task, request.output, request.tokens_per_second)
        return {"ok": True}

    # Validation for non-benchmark tasks (PB-33)
    if request.status == "done":
        ok, msg = val_module.validate_result(task_type, request.output, files)
        db.update_task_validation(task_id, "ok" if ok else "failed", msg)
        if not ok:
            log.warning("Task %d validation failed (%s): %s — requeuing.", task_id, task_type, msg)
            outcome = db.requeue_task(task_id)
            db.log_event("task_validation_failed", project_id=task.get("project_id"),
                         agent_id=task.get("assigned_to"),
                         payload={"task_id": task_id, "outcome": outcome, "message": msg})
            return {"ok": True, "validation": "failed", "message": msg, "requeue_outcome": outcome}

        # Conflict detection (PB-45)
        if files:
            project_id = task.get("project_id")
            if project_id:
                conflicts = conflict_detector.detect_and_save(project_id, task_id, files)
                if conflicts:
                    db.log_event("conflict_detected", project_id=project_id,
                                 agent_id=task.get("assigned_to"),
                                 payload={"task_id": task_id, "conflicts": conflicts})

        # Release any newly unblocked tasks (PB-34)
        scheduler.release_after_completion(task_id)
        db.log_event("task_done", project_id=task.get("project_id"),
                     agent_id=task.get("assigned_to"),
                     payload={"task_id": task_id, "task_type": task_type})

    return {"ok": True, "validation": "ok" if request.status == "done" else "skipped"}


@router.post("/api/tasks/{task_id}/cancel", dependencies=[Depends(require_agent_token)])
def cancel_task(task_id: int):
    """Agent cancels a task it can no longer complete; task is requeued."""
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")
    db.requeue_task(task_id)
    log.info("Task %d cancelled and requeued.", task_id)
    return {"ok": True}


def _score_benchmark_task(task: dict, output: str, tokens_per_second: float | None) -> None:
    """Score a completed benchmark task and save scores to agent_scores."""
    assigned_to = task.get("assigned_to")
    if not assigned_to:
        return

    # The task details contain the benchmark ids to score
    details = task.get("details") or {}
    benchmark_ids: list[str] = details.get("benchmark_ids", [])
    if not benchmark_ids:
        # Try to derive from a single benchmark_id key
        bid = details.get("benchmark_id")
        if bid:
            benchmark_ids = [bid]

    if not benchmark_ids:
        return

    raw_scores: list[tuple[str, float, float]] = []
    for bid in benchmark_ids:
        benchmark = BENCHMARK_BY_ID.get(bid)
        if not benchmark:
            continue
        score, _details = score_response(benchmark, output, tokens_per_second)
        raw_scores.append((benchmark["dimension"], score, benchmark["max_score"]))

    if not raw_scores:
        return

    dim_scores = aggregate_dimension_scores(raw_scores)
    session_id = details.get("eval_session_id")

    for dim, score in dim_scores.items():
        db.save_agent_score(
            agent_id=assigned_to,
            eval_session_id=session_id,
            dimension=dim,
            score=score,
            details={"task_id": task["id"], "benchmark_ids": benchmark_ids},
        )


# ---------------------------------------------------------------------------
# POST /api/eval/start
# ---------------------------------------------------------------------------

class EvalStartRequest(BaseModel):
    agent_id: str | None = None  # None = all online agents


@router.post("/api/eval/start")
def start_eval(request: EvalStartRequest):
    """Create benchmark tasks for online agents and start an eval session."""
    from agents_api import _compute_online

    all_agents = db.list_agents()
    if request.agent_id:
        target_agents = [a for a in all_agents if a["agent_id"] == request.agent_id]
        if not target_agents:
            raise HTTPException(status_code=404, detail="Ajan bulunamadı.")
    else:
        target_agents = [a for a in all_agents if _compute_online(a)]

    if not target_agents:
        raise HTTPException(status_code=400, detail="Çevrimiçi ajan yok.")


    session_id = db.create_eval_session()

    # We need a project to attach tasks to. Use project_id=0 as a sentinel
    # but benchmark tasks don't belong to real projects. We'll use the first
    # available project or skip if none exist. In practice, eval tasks are
    # standalone; we create a minimal ephemeral record approach by creating
    # one task per benchmark per agent using an existing project or creating
    # a dedicated eval project.
    # For simplicity: create one benchmark task per agent covering all dimensions.
    # The task details carry all benchmark_ids for that agent.
    import json
    from datetime import UTC, datetime

    projects = db.list_projects()
    if not projects:
        # Create a placeholder eval project
        project_id = db.create_project("__eval__", "Benchmark evaluation session", None)
    else:
        project_id = projects[0]["id"]

    created_tasks = []
    for agent in target_agents:
        # Create one task per dimension for this agent
        from benchmarks import BENCHMARKS_BY_DIMENSION
        from task_weights import DIMENSIONS

        for dim in DIMENSIONS:
            dim_benchmarks = BENCHMARKS_BY_DIMENSION.get(dim, [])
            if not dim_benchmarks:
                continue
            benchmark_ids = [b["id"] for b in dim_benchmarks]
            # Use the first benchmark question as the task question
            first_b = dim_benchmarks[0]
            task_details = {
                "benchmark_ids": benchmark_ids,
                "dimension": dim,
                "eval_session_id": session_id,
                "benchmark_id": first_b["id"],
            }
            # Insert task directly
            with db.connect() as conn:
                now = datetime.now(UTC).isoformat(timespec="seconds")
                from datetime import timedelta
                expires = (datetime.now(UTC) + timedelta(minutes=5)).isoformat(timespec="seconds")
                cursor = conn.execute(
                    "INSERT INTO tasks (project_id, key, stage, type, title, description, details, "
                    "status, performed_by, assigned_to, assigned_at, lease_expires_at, assignment_reason) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        project_id,
                        f"EVAL-{session_id}-{agent['agent_id']}-{dim}",
                        1,
                        "benchmark",
                        f"Benchmark: {dim} ({agent['agent_id']})",
                        f"Dimension benchmark for agent {agent['agent_id']}",
                        json.dumps(task_details, ensure_ascii=False),
                        "planned",
                        agent["agent_id"],
                        agent["agent_id"],
                        now,
                        expires,
                        json.dumps({"reason": "eval", "eval_session_id": session_id}),
                    ),
                )
                created_tasks.append(cursor.lastrowid)

    return {"eval_session_id": session_id, "tasks_created": len(created_tasks), "agents": [a["agent_id"] for a in target_agents]}
