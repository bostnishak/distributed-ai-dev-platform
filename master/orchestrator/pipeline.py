"""ORC-01, ORC-18, ORC-19: Staged Orchestrator Pipeline & FastAPI Endpoints (each stage <= 150 lines)."""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from access_control import require_local_or_admin
from gateway import (
    CancellationToken,
    LLMClient,
    build_layered_system_prompt,
    default_client,
    get_run_traces,
    is_simple_greeting,
)
from orchestrator.classifier import IntentDecision, classify_intent, load_intent_catalog
from orchestrator.contracts import (
    ContractValidation,
    ResponseContract,
    build_contract,
    enforce_contract,
)
from orchestrator.planner import (
    DAGExecutor,
    ExecutionPlan,
    StepOutcome,
    build_plan,
    dispatch_to_agent_or_local,
)
from orchestrator.state import (
    ConversationState,
    apply_targeted_edit,
    check_clarification_needed,
    feedback_summary,
    filter_relevant_memories,
    get_artifact,
    get_job,
    get_run,
    list_artifacts,
    load_conversation_state,
    make_sse_event,
    record_feedback,
    save_artifact,
    save_conversation_state,
    save_run,
)
from orchestrator.tools_registry import ToolRegistry, default_registry

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])

_INJECTION_RE = re.compile(
    r"(ignore\s+previous\s+instructions|system\s+prompt\s+override|jailbreak|tüm\s+kuralları\s+yok\s+say)",
    re.IGNORECASE,
)
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U00002600-\U000027BF"
    "\U0001FA70-\U0001FAFF"
    "]+",
    flags=re.UNICODE,
)

# ORC-19: Cost-quality tiers
TIER_CONFIG: dict[str, dict[str, Any]] = {
    "fast": {"use_council": False, "verify_llm": False, "max_predict": 512},
    "standard": {"use_council": False, "verify_llm": False, "max_predict": 1536},
    "verified": {"use_council": False, "verify_llm": True, "max_predict": 2048},
    "council": {"use_council": True, "verify_llm": True, "max_predict": 2048},
}


@dataclass
class OrchestratorContext:
    run_id: str
    user_text: str
    user_id: str = "default"
    chat_id: str = ""
    mode_override: str | None = None
    tier_override: str | None = None
    model_override: str | None = None
    outline_approved: bool = False
    approval_granted: bool = False
    memories: list[dict[str, Any] | str] = field(default_factory=list)
    seed: int | None = None
    started_at: float = field(default_factory=time.perf_counter)

    # Stage outputs
    clean_text: str = ""
    is_greeting: bool = False
    blocked_reason: str = ""
    clarification_questions: list[str] = field(default_factory=list)
    filtered_memories: list[dict[str, Any] | str] = field(default_factory=list)
    decision: IntentDecision | None = None
    contract: ResponseContract | None = None
    tier: str = "standard"
    plan: ExecutionPlan | None = None
    step_outcomes: dict[str, StepOutcome] = field(default_factory=dict)
    raw_response: str = ""
    final_response: str = ""
    validation: ContractValidation | None = None
    model_used: str = ""
    provider_used: str = ""
    tools_used: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    conv_state: ConversationState | None = None
    _seq: int = 0

    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        self._seq += 1
        self.events.append(make_sse_event(event_type, data, run_id=self.run_id, seq=self._seq))


# ---------------------------------------------------------------- Stage 1: Preprocess

def stage_preprocess(ctx: OrchestratorContext) -> None:
    ctx.clean_text = re.sub(r"\s+", " ", (ctx.user_text or "").strip())
    ctx.is_greeting = is_simple_greeting(ctx.clean_text)
    if ctx.chat_id:
        ctx.conv_state = load_conversation_state(ctx.chat_id, ctx.user_id)
    ctx.emit("meta", {"chat_id": ctx.chat_id, "user_id": ctx.user_id, "is_greeting": ctx.is_greeting})


# ---------------------------------------------------------------- Stage 2: Guard In

def stage_guard_in(ctx: OrchestratorContext) -> None:
    if not ctx.clean_text:
        ctx.blocked_reason = "Boş istek gönderildi."
        ctx.emit("warning", {"code": "empty_input", "message": ctx.blocked_reason})
        return
    if _INJECTION_RE.search(ctx.clean_text):
        ctx.blocked_reason = "Güvenlik politikası: sistem yönergelerini geçersiz kılma girişimi engellendi."
        ctx.emit("warning", {"code": "prompt_injection_blocked", "message": ctx.blocked_reason})
        return
    if not ctx.is_greeting:
        ctx.filtered_memories = filter_relevant_memories(ctx.clean_text, ctx.memories)


# ---------------------------------------------------------------- Stage 3: Route

def stage_route(ctx: OrchestratorContext) -> None:
    if ctx.blocked_reason:
        return
    decision = classify_intent(ctx.clean_text, mode_override=ctx.mode_override)
    ctx.decision = decision
    ctx.tier = ctx.tier_override if ctx.tier_override in TIER_CONFIG else decision.tier
    ctx.contract = build_contract(
        decision.mode,
        user_text=ctx.clean_text,
        language=decision.language,
        outline_approved=ctx.outline_approved,
    )
    ctx.clarification_questions = check_clarification_needed(decision.intent, ctx.clean_text)
    ctx.emit(
        "route",
        {
            "intent": decision.intent,
            "confidence": decision.confidence,
            "mode": ctx.contract.mode,
            "tier": ctx.tier,
            "language": ctx.contract.language,
            "sub_intents": decision.sub_intents,
        },
    )


# ---------------------------------------------------------------- Stage 4: Plan

def stage_plan(ctx: OrchestratorContext, registry: ToolRegistry) -> None:
    if ctx.blocked_reason or ctx.clarification_questions or ctx.decision is None:
        return
    ctx.plan = build_plan(ctx.decision, ctx.clean_text, registry)
    ctx.emit("plan", ctx.plan.to_dict())


# ---------------------------------------------------------------- Stage 5: Execute

@dataclass
class _ExecEnv:
    ctx: OrchestratorContext
    client: LLMClient
    registry: ToolRegistry
    sys_prompt: str
    max_predict: int
    cancel_token: CancellationToken | None = None


async def _run_plan_step(env: _ExecEnv, step: Any, prior: dict[str, StepOutcome]) -> Any:
    ctx = env.ctx
    if step.action == "tool":
        tr = await env.registry.execute(
            step.tool,
            step.args,
            approval_granted=ctx.approval_granted,
            actor=ctx.user_id,
        )
        ctx.tools_used.append(step.tool)
        if tr.status == "approval_required":
            ctx.emit("approval_required", {"tool": step.tool, "message": tr.error})
        return tr.output if tr.status == "ok" else {"error": tr.error}

    prior_notes = [f"[{k}]: {v.output}" for k, v in prior.items() if v.status == "ok" and v.output]
    user_msg = str(step.args.get("prompt") or ctx.clean_text)
    if prior_notes:
        user_msg = f"{user_msg}\n\nÖnceki adım çıktıları:\n" + "\n".join(prior_notes)
    msgs = [{"role": "system", "content": env.sys_prompt}, {"role": "user", "content": user_msg}]

    async def _local_call() -> str:
        intent = ctx.decision.intent if ctx.decision else "genel"
        res = await env.client.chat(
            msgs,
            model=ctx.model_override,
            task_type=intent,
            user_id=ctx.user_id,
            run_id=ctx.run_id,
            feature=f"orchestrator:{intent if ctx.decision else 'chat'}",
            seed=ctx.seed,
            num_predict=env.max_predict,
            cancel_token=env.cancel_token,
        )
        ctx.model_used = res.model
        ctx.provider_used = res.provider
        return res.content

    if step.action == "agent":
        dispatched = await dispatch_to_agent_or_local(
            prompt=user_msg,
            capability=step.capability,
            local_fallback=_local_call,
            poll_timeout_s=0.3,
        )
        if not ctx.provider_used:
            ctx.provider_used = dispatched["source"]
        return dispatched["content"]
    return await _local_call()


async def stage_execute(
    ctx: OrchestratorContext,
    client: LLMClient,
    registry: ToolRegistry,
    *,
    cancel_token: CancellationToken | None = None,
) -> None:
    if ctx.blocked_reason:
        ctx.raw_response = ctx.blocked_reason
        return
    if ctx.clarification_questions:
        lines = ["Devam etmeden önce eksik kritik bilgileri netleştirelim:"]
        lines.extend(f"{i}. {q}" for i, q in enumerate(ctx.clarification_questions, start=1))
        ctx.raw_response = "\n".join(lines)
        return
    if ctx.decision is None or ctx.contract is None or ctx.plan is None:
        raise RuntimeError("Orchestrator stage_execute requires route and plan stages to complete first.")

    mem_texts = [m["fact"] if isinstance(m, dict) else m for m in ctx.filtered_memories]
    sys_prompt, _layers = build_layered_system_prompt(
        mode_name=ctx.contract.mode,
        mode_rules=f"Yanıt dili: {ctx.contract.language}. Biçim yönergeleri: {', '.join(ctx.contract.format_directives) or 'yok'}.",
        memory_block="\n".join(f"- {m}" for m in mem_texts),
        user_prompt=ctx.clean_text,
    )
    tier_cfg = TIER_CONFIG.get(ctx.tier, TIER_CONFIG["standard"])
    env = _ExecEnv(
        ctx=ctx,
        client=client,
        registry=registry,
        sys_prompt=sys_prompt,
        max_predict=int(tier_cfg["max_predict"]),
        cancel_token=cancel_token,
    )

    async def _run_step(step: Any, prior: dict[str, StepOutcome]) -> Any:
        return await _run_plan_step(env, step, prior)

    async def _on_dag_evt(etype: str, payload: dict[str, Any]) -> None:
        ctx.emit(etype, payload)

    executor = DAGExecutor()
    ctx.step_outcomes = await executor.execute(ctx.plan, registry, _run_step, on_event=_on_dag_evt)
    parts = [o.output for o in ctx.step_outcomes.values() if o.status == "ok" and isinstance(o.output, str)]
    ctx.raw_response = "\n\n".join(parts).strip()


# ---------------------------------------------------------------- Stage 6: Verify

async def stage_verify(ctx: OrchestratorContext, client: LLMClient) -> None:
    cleaned = _EMOJI_RE.sub("", ctx.raw_response or "").strip()
    if ctx.blocked_reason or ctx.clarification_questions or ctx.contract is None:
        ctx.final_response = cleaned
        return

    tier_cfg = TIER_CONFIG.get(ctx.tier, TIER_CONFIG["standard"])

    async def _llm_repair(draft: str, violations: list[str]) -> str:
        repair_prompt = (
            f"Aşağıdaki yanıt şu sözleşme ihlallerini içeriyor: {', '.join(violations)}.\n"
            f"Mod: {ctx.contract.mode}. Dili koru ({ctx.contract.language}), emoji kullanma ve ihlalleri düzelt:\n\n{draft}"
        )
        res = await client.chat(
            [{"role": "user", "content": repair_prompt}],
            model=ctx.model_override,
            task_type="factual",
            user_id=ctx.user_id,
            run_id=ctx.run_id,
            feature="contract_repair",
            seed=ctx.seed,
        )
        return _EMOJI_RE.sub("", res.content).strip()

    repair_fn = _llm_repair if tier_cfg["verify_llm"] else None
    fixed, val = await enforce_contract(cleaned, ctx.contract, llm_repair_fn=repair_fn)
    ctx.final_response = fixed
    ctx.validation = val
    ctx.citations = re.findall(r"(\[\d+\]|\[Kaynak:[^\]]+\]|https?://\S+)", fixed)
    ctx.emit(
        "verification",
        {"passed": val.passed, "mode": val.mode, "violations": val.violations, "citations": len(ctx.citations)},
    )


# ---------------------------------------------------------------- Stage 7: Render

def stage_render(ctx: OrchestratorContext) -> None:
    if ctx.final_response:
        ctx.emit("token", {"content": ctx.final_response})
    for c in ctx.citations:
        ctx.emit("citation", {"ref": c})

    # Register standalone artifact for presentation/document/project/code_only outputs (ORC-13)
    if ctx.decision and ctx.decision.mode in {"presentation", "project", "code_only"} and ctx.final_response:
        sections = [s.strip() for s in re.split(r"\n{2,}", ctx.final_response) if s.strip()]
        art = save_artifact(
            kind=ctx.decision.mode,
            title=ctx.clean_text[:80],
            sections=sections or [ctx.final_response],
            content=ctx.final_response,
            chat_id=ctx.chat_id,
            user_id=ctx.user_id,
            metadata={"intent": ctx.decision.intent, "run_id": ctx.run_id},
        )
        ctx.artifacts.append(art)
        ctx.emit("artifact", {"artifact_id": art["artifact_id"], "kind": art["kind"], "version": art["version"]})

    latency_ms = int((time.perf_counter() - ctx.started_at) * 1000)
    ctx.emit(
        "done",
        {
            "run_id": ctx.run_id,
            "model": ctx.model_used,
            "provider": ctx.provider_used,
            "latency_ms": latency_ms,
            "artifact_count": len(ctx.artifacts),
        },
    )


# ---------------------------------------------------------------- Stage 8: Persist

def stage_persist(ctx: OrchestratorContext) -> None:
    latency_ms = int((time.perf_counter() - ctx.started_at) * 1000)
    save_run({
        "run_id": ctx.run_id,
        "chat_id": ctx.chat_id,
        "user_id": ctx.user_id,
        "prompt": ctx.clean_text,
        "intent": ctx.decision.intent if ctx.decision else "blocked",
        "mode": ctx.contract.mode if ctx.contract else "general",
        "tier": ctx.tier,
        "model": ctx.model_used,
        "provider": ctx.provider_used,
        "seed": ctx.seed,
        "plan": ctx.plan.to_dict() if ctx.plan else {},
        "tools_used": ctx.tools_used,
        "citations": ctx.citations,
        "verification": {
            "passed": ctx.validation.passed if ctx.validation else True,
            "violations": ctx.validation.violations if ctx.validation else [],
        },
        "response_text": ctx.final_response,
        "latency_ms": latency_ms,
    })
    if ctx.chat_id:
        st = ctx.conv_state or load_conversation_state(ctx.chat_id, ctx.user_id)
        st.turn_count += 1
        if ctx.contract:
            st.active_mode = ctx.contract.mode
        if st.turn_count == 1 and ctx.clean_text:
            st.goals.append(ctx.clean_text[:120])
        for a in ctx.artifacts:
            st.artifact_ids.append(a["artifact_id"])
        save_conversation_state(st)


# ---------------------------------------------------------------- Pipeline Entrypoint

async def run_pipeline(user_text: str, **opts: Any) -> OrchestratorContext:
    """ORC-01: Execute the 8-stage orchestrator pipeline cleanly end-to-end."""
    ctx = OrchestratorContext(
        run_id=f"run-{uuid.uuid4().hex[:10]}",
        user_text=user_text,
        user_id=str(opts.get("user_id", "default")),
        chat_id=str(opts.get("chat_id", "")),
        mode_override=opts.get("mode_override"),
        tier_override=opts.get("tier_override"),
        model_override=opts.get("model_override"),
        outline_approved=bool(opts.get("outline_approved", False)),
        approval_granted=bool(opts.get("approval_granted", False)),
        memories=list(opts.get("memories") or []),
        seed=opts.get("seed"),
    )
    llm_client: LLMClient = opts.get("client") or default_client
    tool_reg: ToolRegistry = opts.get("registry") or default_registry
    cancel_token: CancellationToken | None = opts.get("cancel_token")

    stage_preprocess(ctx)
    stage_guard_in(ctx)
    stage_route(ctx)
    stage_plan(ctx, tool_reg)
    await stage_execute(ctx, llm_client, tool_reg, cancel_token=cancel_token)
    await stage_verify(ctx, llm_client)
    stage_render(ctx)
    stage_persist(ctx)
    return ctx


# ---------------------------------------------------------------- FastAPI Routes (SEC-22 Compliant)

class RunRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    user_id: str = "default"
    chat_id: str = ""
    mode: str | None = None
    tier: str | None = None
    model: str | None = None
    outline_approved: bool = False
    approval_granted: bool = False
    seed: int | None = None


class TargetedEditRequest(BaseModel):
    section_index: int = Field(..., ge=0)
    content: str = Field(..., min_length=1)


class FeedbackRequest(BaseModel):
    run_id: str
    rating: int
    reason_tags: list[str] = Field(default_factory=list)
    note: str = ""
    user_id: str = "default"


@router.get("/intents")
async def api_list_intents():
    version, specs = load_intent_catalog()
    return {
        "version": version,
        "count": len(specs),
        "intents": [
            {"id": s.id, "route": s.route, "mode": s.mode, "tier": s.tier, "risk": s.risk, "tools": list(s.tools)}
            for s in specs.values()
        ],
    }


@router.get("/tools")
async def api_list_tools():
    return {"tools": default_registry.list_specs()}


_LOCAL_OR_ADMIN = [Depends(require_local_or_admin)]


@router.post("/run", dependencies=_LOCAL_OR_ADMIN)
async def api_run_orchestrator(body: RunRequest):
    ctx = await run_pipeline(
        body.prompt,
        user_id=body.user_id,
        chat_id=body.chat_id,
        mode_override=body.mode,
        tier_override=body.tier,
        model_override=body.model,
        outline_approved=body.outline_approved,
        approval_granted=body.approval_granted,
        seed=body.seed,
    )
    return {
        "run_id": ctx.run_id,
        "intent": ctx.decision.intent if ctx.decision else "blocked",
        "mode": ctx.contract.mode if ctx.contract else "general",
        "tier": ctx.tier,
        "model": ctx.model_used,
        "provider": ctx.provider_used,
        "response": ctx.final_response,
        "verification": ctx.validation.__dict__ if ctx.validation else {"passed": True, "violations": []},
        "artifacts": ctx.artifacts,
        "events": ctx.events,
    }


@router.get("/runs/{run_id}")
async def api_get_run(run_id: str):
    """ORC-23: 'Bu yanıt nasıl üretildi' provenance inspection."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Çalıştırma kaydı bulunamadı.")
    run["gateway_traces"] = get_run_traces(run_id)
    return run


@router.post("/runs/{run_id}/replay", dependencies=_LOCAL_OR_ADMIN)
async def api_replay_run(run_id: str):
    """ORC-23: Re-execute a stored run using its original prompt, mode, tier, model, and seed."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Çalıştırma kaydı bulunamadı.")
    ctx = await run_pipeline(
        run["prompt"],
        user_id=run["user_id"],
        chat_id=run["chat_id"],
        mode_override=run["mode"],
        tier_override=run["tier"],
        model_override=run["model"] or None,
        seed=run.get("seed"),
    )
    return {"original_run_id": run_id, "replay_run_id": ctx.run_id, "response": ctx.final_response}


@router.get("/jobs/{job_id}")
async def api_get_job(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="İş kaydı bulunamadı.")
    return job


@router.get("/artifacts")
async def api_list_artifacts(user_id: str = "default", chat_id: str | None = None):
    return {"artifacts": list_artifacts(user_id=user_id, chat_id=chat_id)}


@router.get("/artifacts/{artifact_id}")
async def api_get_artifact(artifact_id: str):
    art = get_artifact(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Artefakt bulunamadı.")
    return art


@router.get("/artifacts/{artifact_id}/versions")
async def api_artifact_versions(artifact_id: str):
    from orchestrator.state import list_artifact_versions

    if not get_artifact(artifact_id):
        raise HTTPException(status_code=404, detail="Artefakt bulunamadı.")
    return {"artifact_id": artifact_id, "versions": list_artifact_versions(artifact_id)}


@router.post("/artifacts/{artifact_id}/edit", dependencies=_LOCAL_OR_ADMIN)
async def api_edit_artifact(artifact_id: str, body: TargetedEditRequest):
    try:
        return apply_targeted_edit(artifact_id, body.section_index, body.content)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IndexError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/feedback", dependencies=_LOCAL_OR_ADMIN)
async def api_submit_feedback(body: FeedbackRequest):
    return record_feedback(
        body.run_id,
        body.rating,
        reason_tags=body.reason_tags,
        note=body.note,
        user_id=body.user_id,
    )


@router.get("/feedback/summary")
async def api_feedback_summary():
    return feedback_summary()
