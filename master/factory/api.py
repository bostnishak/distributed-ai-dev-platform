"""FastAPI router for Unified Software Factory (`master/factory/`): IDE-01..IDE-24 (SEC-22 Compliant)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import config
from access_control import require_local_or_admin
from factory.pipeline import (
    build_and_verify_project,
    compute_and_apply_hunks,
    generate_prd_plan,
    package_project,
    scan_workspace_sast,
)
from factory.templates import STARTER_TEMPLATES

router = APIRouter(prefix="/api/factory", tags=["factory"])
_LOCAL_OR_ADMIN = [Depends(require_local_or_admin)]


class PlanReq(BaseModel):
    prompt: str = Field(..., min_length=2)
    project_name: str = "YeniProje"
    template_id: str | None = None
    auto_approve: bool = False


class BuildReq(BaseModel):
    prompt: str = Field(..., min_length=2)
    project_name: str = "YeniProje"
    template_id: str | None = None
    custom_files: dict[str, str] = Field(default_factory=dict)


class HunkDiffReq(BaseModel):
    old_text: str
    new_text: str
    accepted_hunks: list[int] | None = None


@router.get("/templates")
async def api_list_templates():
    return {
        "count": len(STARTER_TEMPLATES),
        "templates": [{"id": k, "name": v["name"], "stack": v["stack"], "files": sorted(v["files"].keys())} for k, v in STARTER_TEMPLATES.items()],
    }


@router.post("/plan", dependencies=_LOCAL_OR_ADMIN)
async def api_create_plan(body: PlanReq):
    plan = generate_prd_plan(body.prompt, project_name=body.project_name, template_id=body.template_id, auto_approve=body.auto_approve)
    return plan.__dict__


@router.post("/build", dependencies=_LOCAL_OR_ADMIN)
async def api_build_project(body: BuildReq):
    plan = generate_prd_plan(body.prompt, project_name=body.project_name, template_id=body.template_id, auto_approve=True)
    ws_dir = Path(config.DATA_DIR) / "factory_workspaces" / plan.plan_id
    return build_and_verify_project(plan, workspace_dir=ws_dir, custom_files=body.custom_files or None, run_tests=True)


@router.post("/hunk-diff", dependencies=_LOCAL_OR_ADMIN)
async def api_hunk_diff(body: HunkDiffReq):
    acc = set(body.accepted_hunks) if body.accepted_hunks is not None else None
    return compute_and_apply_hunks(body.old_text, body.new_text, accepted_hunk_indices=acc)


@router.post("/workspaces/{plan_id}/package", dependencies=_LOCAL_OR_ADMIN)
async def api_package_workspace(plan_id: str, target: str = "zip"):
    ws_dir = Path(config.DATA_DIR) / "factory_workspaces" / plan_id
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")
    return package_project(ws_dir, target=target, project_name=plan_id)


@router.post("/workspaces/{plan_id}/sast", dependencies=_LOCAL_OR_ADMIN)
async def api_sast_workspace(plan_id: str):
    ws_dir = Path(config.DATA_DIR) / "factory_workspaces" / plan_id
    if not ws_dir.is_dir():
        raise HTTPException(status_code=404, detail="Çalışma alanı bulunamadı.")
    return scan_workspace_sast(ws_dir)
