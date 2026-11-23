"""FastAPI router for Domain Engines & Zero-Code YAML Domain Specs (`master/domains/`): DOM-01..DOM-12 (SEC-22)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from access_control import require_local_or_admin
from domains.engines import (
    DimensionalityError,
    MissingDomainInputsError,
    UnitQuantity,
    analyze_legal_contract,
    compute_kienzle_cutting_force,
    evaluate_health_query,
    run_finance_dcf,
    validate_gcode_safety,
)
from domains.registry import load_all_domain_specs

router = APIRouter(prefix="/api/domains", tags=["domains"])
_LOCAL_OR_ADMIN = [Depends(require_local_or_admin)]


class UnitConvertReq(BaseModel):
    value: float
    from_unit: str
    to_unit: str


class HealthReq(BaseModel):
    query: str
    trusted_sources: list[dict[str, Any]] = []


class GCodeReq(BaseModel):
    gcode: str


@router.get("/specs")
async def api_list_domain_specs():
    specs = load_all_domain_specs()
    return {"count": len(specs), "domains": [{"id": k, "name": v["name"], "risk_level": v["risk_level"], "eval_count": len(v["eval_questions"])} for k, v in specs.items()]}


@router.post("/finance/dcf", dependencies=_LOCAL_OR_ADMIN)
async def api_finance_dcf(payload: dict[str, Any]):
    try:
        return run_finance_dcf(payload)
    except MissingDomainInputsError as exc:
        raise HTTPException(status_code=422, detail={"missing": exc.missing_fields, "questions": exc.questions}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/legal/analyze", dependencies=_LOCAL_OR_ADMIN)
async def api_legal_analyze(payload: dict[str, Any]):
    try:
        return analyze_legal_contract(payload)
    except MissingDomainInputsError as exc:
        raise HTTPException(status_code=422, detail={"missing": exc.missing_fields, "questions": exc.questions}) from exc


@router.post("/health/info", dependencies=_LOCAL_OR_ADMIN)
async def api_health_info(body: HealthReq):
    return evaluate_health_query(body.query, trusted_sources=body.trusted_sources)


@router.post("/engineering/convert", dependencies=_LOCAL_OR_ADMIN)
async def api_unit_convert(body: UnitConvertReq):
    try:
        res = UnitQuantity(body.value, body.from_unit).to(body.to_unit)
        return {"value": res.value, "unit": res.unit}
    except DimensionalityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cnc/kienzle", dependencies=_LOCAL_OR_ADMIN)
async def api_cnc_kienzle(payload: dict[str, Any]):
    try:
        return compute_kienzle_cutting_force(payload)
    except MissingDomainInputsError as exc:
        raise HTTPException(status_code=422, detail={"missing": exc.missing_fields, "questions": exc.questions}) from exc


@router.post("/cnc/gcode/validate", dependencies=_LOCAL_OR_ADMIN)
async def api_validate_gcode(body: GCodeReq):
    return validate_gcode_safety(body.gcode)
