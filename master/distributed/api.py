"""FastAPI router for Distributed Agents (`master/distributed/`): DIST-01..DIST-22 (SEC-22 Compliant)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import db
from access_control import require_local_or_admin
from distributed.core import (
    INTENT_TO_TASK_TYPE,
    TASK_TYPE_WEIGHTS,
    AgentProfile,
    ThompsonBanditRouter,
    build_benchmark_tasks,
    build_performance_matrix,
    select_distributed_agent,
    three_way_merge,
)
from distributed.network import diagnose_tailscale_failure, generate_agent_install_command

router = APIRouter(prefix="/api/distributed", tags=["distributed"])
_LOCAL_OR_ADMIN = [Depends(require_local_or_admin)]


class SelectAgentReq(BaseModel):
    task_type: str = "backend"
    required_param_b: float = 4.0
    agents: list[AgentProfile]


class MergeReq(BaseModel):
    base: str
    ours: str
    theirs: str


class TailscaleDiagReq(BaseModel):
    probes: dict[str, Any] = Field(default_factory=dict)


@router.get("/taxonomy")
async def api_taxonomy():
    return {"intent_to_task_type": INTENT_TO_TASK_TYPE, "task_type_weights": TASK_TYPE_WEIGHTS}


@router.get("/benchmarks/tasks")
async def api_benchmark_tasks():
    tasks = build_benchmark_tasks()
    return {"count": len(tasks), "tasks": tasks}


@router.get("/agents/stream")
async def api_agents_sse_stream():
    """DIST-11: Live SSE snapshot stream of registered agents and telemetry (no polling required)."""
    async def _gen():
        try:
            agents = db.list_agents() if hasattr(db, "list_agents") else []
        except Exception:
            agents = []
        payload = {"type": "agents_snapshot", "count": len(agents), "agents": agents}
        yield f"event: agents_snapshot\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")


@router.get("/performance")
async def api_performance_matrix():
    return build_performance_matrix()


@router.get("/performance.csv")
async def api_performance_csv():
    data = build_performance_matrix()
    return Response(content=data["csv"], media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="agent_performance.csv"'})


@router.get("/setup-command")
async def api_setup_command(master_url: str = "http://127.0.0.1:8000", os_type: str = "windows", model: str = "qwen2.5-coder:7b"):
    return generate_agent_install_command(master_url, os_type=os_type, model=model)


@router.post("/select", dependencies=_LOCAL_OR_ADMIN)
async def api_select_agent(body: SelectAgentReq):
    bandit = ThompsonBanditRouter(enabled=True)
    return select_distributed_agent(body.agents, task_type=body.task_type, required_param_b=body.required_param_b, bandit=bandit)


@router.post("/conflicts/merge", dependencies=_LOCAL_OR_ADMIN)
async def api_merge_conflict(body: MergeReq):
    return three_way_merge(body.base, body.ours, body.theirs)


@router.post("/diagnose/tailscale", dependencies=_LOCAL_OR_ADMIN)
async def api_diagnose_tailscale(body: TailscaleDiagReq):
    return diagnose_tailscale_failure(body.probes)
