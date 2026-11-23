"""FastAPI router for Parca 4 Studios (RES, PPT, DOC, DS, MM) — SEC-22 Compliant."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from access_control import require_local_or_admin
from studios.data_science import forecast_with_backtest, profile_dataset_on_demand, select_and_run_stat_test
from studios.documents import DOCUMENT_TEMPLATES, audit_document_quality
from studios.multimedia import anonymize_kvkk_text, default_media_manager, validate_and_repair_diagram
from studios.presentation import DESIGN_THEMES, SLIDE_LAYOUTS, build_narrative_outline
from studios.research import RESEARCH_SPEED_MODES, run_deep_research

router = APIRouter(prefix="/api/studios", tags=["studios"])
_LOCAL_OR_ADMIN = [Depends(require_local_or_admin)]


class ResearchReq(BaseModel):
    topic: str = Field(..., min_length=2)
    speed_mode: str = "fast"
    citation_style: str = "apa"


class ProfileReq(BaseModel):
    rows: list[dict[str, Any]]
    headers: list[str] | None = None


class ForecastReq(BaseModel):
    series: list[float]
    horizon: int = Field(3, ge=1, le=24)


class StatTestReq(BaseModel):
    group_a: list[float]
    group_b: list[float]


class AnonymizeReq(BaseModel):
    text: str


class DiagramReq(BaseModel):
    code: str
    kind: str = "mermaid"


@router.get("/capabilities")
async def api_studio_capabilities():
    return {
        "research_speed_modes": RESEARCH_SPEED_MODES,
        "presentation_themes": list(DESIGN_THEMES.keys()),
        "presentation_layouts": list(SLIDE_LAYOUTS),
        "document_templates": list(DOCUMENT_TEMPLATES.keys()),
    }


@router.post("/research", dependencies=_LOCAL_OR_ADMIN)
async def api_run_research(body: ResearchReq):
    rep = await run_deep_research(body.topic, speed_mode=body.speed_mode, citation_style=body.citation_style)
    return {
        "artifact_id": rep.artifact_id,
        "topic": rep.topic,
        "speed_mode": rep.speed_mode,
        "source_count": len(rep.notes),
        "diversity_score": rep.diversity_score,
        "verification_summary": rep.verification_summary,
        "markdown": rep.markdown,
    }


@router.post("/presentation/outline", dependencies=_LOCAL_OR_ADMIN)
async def api_presentation_outline(topic: str, duration_minutes: int = 9):
    out = build_narrative_outline(topic, duration_minutes=duration_minutes)
    return {
        "topic": out["topic"],
        "slide_count": out["slide_count"],
        "slides": [s.__dict__ for s in out["slides"]],
    }


@router.post("/documents/audit", dependencies=_LOCAL_OR_ADMIN)
async def api_audit_doc(text: str):
    return audit_document_quality(text)


@router.post("/data/profile", dependencies=_LOCAL_OR_ADMIN)
async def api_profile_data(body: ProfileReq):
    return profile_dataset_on_demand(body.rows, headers=body.headers)


@router.post("/data/forecast", dependencies=_LOCAL_OR_ADMIN)
async def api_forecast_data(body: ForecastReq):
    return forecast_with_backtest(body.series, horizon=body.horizon)


@router.post("/data/stat-test", dependencies=_LOCAL_OR_ADMIN)
async def api_stat_test(body: StatTestReq):
    try:
        return select_and_run_stat_test(body.group_a, body.group_b)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/media/anonymize", dependencies=_LOCAL_OR_ADMIN)
async def api_anonymize_kvkk(body: AnonymizeReq):
    return anonymize_kvkk_text(body.text)


@router.post("/media/diagram/validate", dependencies=_LOCAL_OR_ADMIN)
async def api_validate_diagram(body: DiagramReq):
    return validate_and_repair_diagram(body.code, kind=body.kind)


@router.get("/media/{media_id}")
async def api_get_signed_media(media_id: str, user_id: str, exp: int, sig: str):
    """MM-14: Signed, user-authorized, TTL-checked media download endpoint."""
    try:
        item = default_media_manager.fetch_authorized(media_id, requester_id=user_id, exp=exp, sig=sig)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=item["bytes"],
        media_type=item["content_type"],
        headers={"Content-Disposition": f'inline; filename="{item["filename"]}"'},
    )
