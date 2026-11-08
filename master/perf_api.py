"""Performance metrics and dashboard data API (PB-52, PB-51)."""

from __future__ import annotations

from fastapi import APIRouter

import db

router = APIRouter(tags=["performance"])


@router.get("/api/perf/stats")
def perf_stats(project_id: int | None = None):
    """Return aggregate performance metrics for completed tasks."""
    return db.get_perf_stats(project_id)


@router.get("/api/dashboard")
def dashboard():
    """Return a summary for the live dashboard: agent counts, recent events, project overview."""
    from agents_api import _compute_online

    agents = db.list_agents()
    online = sum(1 for a in agents if _compute_online(a))
    busy = sum(1 for a in agents if a.get("heartbeat_status") == "busy" and _compute_online(a))
    projects = db.list_projects()
    active_projects = sum(1 for p in projects if p["status"] not in ("failed",))
    events = db.list_events(limit=20)

    return {
        "agents": {
            "total": len(agents),
            "online": online,
            "busy": busy,
            "offline": len(agents) - online,
        },
        "projects": {
            "total": len(projects),
            "active": active_projects,
        },
        "recent_events": events,
        "perf": db.get_perf_stats(),
    }


@router.get("/api/projects/{project_id}/conflicts")
def list_conflicts(project_id: int):
    """Return file conflicts detected in this project."""
    return db.list_conflicts(project_id)


@router.post("/api/projects/{project_id}/conflicts/{conflict_id}/resolve")
def resolve_conflict(project_id: int, conflict_id: int, resolution: str = "manual"):
    """Mark a conflict as resolved."""
    ok = db.resolve_conflict(conflict_id, resolution)
    return {"ok": ok}


@router.get("/api/events")
def list_events(limit: int = 50, project_id: int | None = None):
    """Return recent platform events (task assignments, completions, conflicts)."""
    return db.list_events(limit=min(limit, 200), project_id=project_id)
