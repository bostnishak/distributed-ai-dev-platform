"""ML-01..ML-13: FastAPI Endpoints for Drift, Active Learning, DPO Export & Eval-Gated Model Registry (SEC-22 Compliant)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from access_control import require_local_or_admin
from hallucination.eval_runner import GOLDEN_PATH, ensure_eval_datasets, load_jsonl
from hallucination.verifier import list_approved_corrections
from ml_ops.models import (
    build_dpo_dataset,
    detect_distribution_drift,
    evaluate_canary_health,
    list_active_learning_queue,
    list_registered_models,
    register_and_gate_adapter,
)

router = APIRouter(prefix="/api/ml", tags=["ml_ops"])
_LOCAL_OR_ADMIN = [Depends(require_local_or_admin)]


class DriftReq(BaseModel):
    baseline_counts: dict[str, int]
    current_counts: dict[str, int]


class RegisterAdapterReq(BaseModel):
    base_model: str
    adapter_name: str
    dataset_hash: str
    hyperparams: dict[str, Any] = Field(default_factory=dict)
    eval_report_path: str = ""
    eval_score: float
    baseline_score: float


class CanaryCheckReq(BaseModel):
    canary_error_rate: float
    baseline_error_rate: float


@router.get("/models")
async def api_list_models():
    return {"models": list_registered_models()}


@router.post("/models/register", dependencies=_LOCAL_OR_ADMIN)
async def api_register_adapter(body: RegisterAdapterReq):
    return register_and_gate_adapter(
        base_model=body.base_model,
        adapter_name=body.adapter_name,
        dataset_hash=body.dataset_hash,
        hyperparams=body.hyperparams,
        eval_report_path=body.eval_report_path,
        eval_score=body.eval_score,
        baseline_score=body.baseline_score,
    )


@router.post("/models/{model_id}/canary-check", dependencies=_LOCAL_OR_ADMIN)
async def api_canary_check(model_id: str, body: CanaryCheckReq):
    return evaluate_canary_health(
        model_id,
        canary_error_rate=body.canary_error_rate,
        baseline_error_rate=body.baseline_error_rate,
    )


@router.post("/drift", dependencies=_LOCAL_OR_ADMIN)
async def api_check_drift(body: DriftReq):
    return detect_distribution_drift(body.baseline_counts, body.current_counts)


@router.get("/active-learning")
async def api_active_learning(limit: int = 20):
    return {"items": list_active_learning_queue(limit=limit)}


@router.post("/dpo/export", dependencies=_LOCAL_OR_ADMIN)
async def api_export_dpo():
    ensure_eval_datasets()
    golden_prompts = {r["prompt"] for r in load_jsonl(GOLDEN_PATH)}
    approved = list_approved_corrections()
    return build_dpo_dataset(approved, golden_prompts=golden_prompts)
