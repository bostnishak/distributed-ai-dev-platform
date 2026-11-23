"""HAL-25, HAL-26, HAL-28, HAL-30: Hallucination Verification, Report Queue, Telemetry & Reliability Limits API."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from access_control import require_local_or_admin
from hallucination.eval_runner import REPORTS_DIR, ensure_eval_datasets
from hallucination.verifier import (
    HALLUCINATION_TAXONOMY,
    approve_wrong_answer_report,
    audit_python_code_apis,
    detect_false_premise,
    enforce_citation_policy,
    get_model_hallucination_profiles,
    submit_wrong_answer_report,
    telemetry_summary_7d,
    verify_numbers_and_tables,
)

router = APIRouter(prefix="/api/hallucination", tags=["hallucination"])
_LOCAL_OR_ADMIN = [Depends(require_local_or_admin)]


class VerifyPayload(BaseModel):
    text: str = Field(..., min_length=1)
    question: str = ""
    sources: list[dict[str, Any]] = Field(default_factory=list)
    strict: bool = False
    code_lang: str | None = None


class WrongReportReq(BaseModel):
    run_id: str
    prompt: str
    bad_answer: str
    corrected_answer: str
    source_url: str = ""
    taxonomy_class: str = "fabricated_fact"


@router.get("/taxonomy")
async def api_taxonomy():
    return {"taxonomy": HALLUCINATION_TAXONOMY}


@router.post("/verify", dependencies=_LOCAL_OR_ADMIN)
async def api_verify(body: VerifyPayload):
    cite_res = enforce_citation_policy(body.text, body.sources, strict=body.strict)
    num_res = verify_numbers_and_tables(body.text, body.sources)
    premise = detect_false_premise(body.question) if body.question else {"false_premise": False, "correction": ""}
    code_audit = audit_python_code_apis(body.text) if body.code_lang == "python" else None
    return {
        "citations": cite_res,
        "numbers": num_res,
        "premise": premise,
        "code_audit": code_audit,
    }


@router.get("/telemetry")
async def api_telemetry():
    return telemetry_summary_7d()


@router.get("/profiles")
async def api_model_profiles():
    return {"profiles": get_model_hallucination_profiles()}


@router.post("/reports", dependencies=_LOCAL_OR_ADMIN)
async def api_submit_report(body: WrongReportReq):
    return submit_wrong_answer_report(
        run_id=body.run_id,
        prompt=body.prompt,
        bad_answer=body.bad_answer,
        corrected_answer=body.corrected_answer,
        source_url=body.source_url,
        taxonomy_class=body.taxonomy_class,
    )


@router.post("/reports/{report_id}/approve", dependencies=_LOCAL_OR_ADMIN)
async def api_approve_report(report_id: str):
    row = approve_wrong_answer_report(report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Bildirim bulunamadı.")
    return row


@router.get("/reliability")
async def api_reliability_limits():
    """HAL-30: Transparent reliability status pulling live metrics directly from latest eval report."""
    ensure_eval_datasets()
    latest_report: dict[str, Any] = {}
    candidates = sorted(REPORTS_DIR.glob("eval_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if candidates:
        latest_report = json.loads(candidates[0].read_text(encoding="utf-8"))
    return {
        "taxonomy": HALLUCINATION_TAXONOMY,
        "latest_eval": latest_report,
        "telemetry_7d": telemetry_summary_7d(),
        "honest_limits": [
            "4B-9B yerel modeller dünya bilgisinde bulut öncü modellerine ulaşamaz; olgusal doğruluk RAG ve araçlarla sağlanır.",
            "Web erişimi kapalıyken güncel olaylar doğrulanamaz ve sistem bunu açıkça bildirir.",
            "İnce ayar olgusal bilgi ezberletmek için değil; biçim, araç kullanımı ve kaçınma davranışı için kullanılır.",
        ],
    }
