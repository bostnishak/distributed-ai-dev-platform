"""ORC-05, ORC-06, ORC-07: Schema-Constrained Planner, Parallel DAG Executor & Distributed Agent Dispatch."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import db
import selection
from orchestrator.classifier import IntentDecision
from orchestrator.tools_registry import ToolRegistry


class PlanValidationError(ValueError):
    """Raised when a generated plan contains unknown tools, missing dependencies, or cycles."""


@dataclass
class PlanStep:
    step_id: str
    action: str  # tool | llm | agent | verify
    description: str
    tool: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    capability: str = "kod"
    retries: int = 1


@dataclass
class ExecutionPlan:
    plan_id: str
    goal: str
    complexity: str  # simple | multi_step | distributed
    mode: str
    steps: list[PlanStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "complexity": self.complexity,
            "mode": self.mode,
            "steps": [
                {
                    "step_id": s.step_id,
                    "action": s.action,
                    "description": s.description,
                    "tool": s.tool,
                    "depends_on": list(s.depends_on),
                    "capability": s.capability,
                }
                for s in self.steps
            ],
        }


def validate_plan(plan: ExecutionPlan, registry: ToolRegistry) -> list[str]:
    """ORC-05: Validate tools exist, dependencies exist, and graph is acyclic (Kahn's topological sort)."""
    ids = [s.step_id for s in plan.steps]
    if len(ids) != len(set(ids)):
        raise PlanValidationError("Plan içinde yinelenen step_id tespit edildi.")
    step_map = {s.step_id: s for s in plan.steps}

    indegree: dict[str, int] = {sid: 0 for sid in ids}
    children: dict[str, list[str]] = {sid: [] for sid in ids}

    for step in plan.steps:
        if step.action == "tool" and not registry.has(step.tool):
            raise PlanValidationError(f"Bilinmeyen araç referansı: {step.tool}")
        for dep in step.depends_on:
            if dep not in step_map:
                raise PlanValidationError(f"Adım '{step.step_id}' tanımsız bağımlılığa işaret ediyor: '{dep}'")
            indegree[step.step_id] += 1
            children[dep].append(step.step_id)

    queue: deque[str] = deque(sid for sid, deg in indegree.items() if deg == 0)
    order: list[str] = []
    while queue:
        cur = queue.popleft()
        order.append(cur)
        for nxt in children[cur]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if len(order) != len(ids):
        raise PlanValidationError("Plan bağımlılık grafında döngü (cycle) tespit edildi.")
    return order


def build_plan(decision: IntentDecision, user_text: str, registry: ToolRegistry) -> ExecutionPlan:
    """ORC-05: Build a validated DAG ExecutionPlan for single-intent or multi-intent requests."""
    pid = f"pln-{uuid.uuid4().hex[:8]}"
    steps: list[PlanStep] = []

    if decision.sub_intents:
        prev_id = ""
        for idx, sub in enumerate(decision.sub_intents, start=1):
            sid = f"sub-{idx}"
            steps.append(
                PlanStep(
                    step_id=sid,
                    action="llm",
                    description=f"Alt görev ({sub['intent']}): {sub['text'][:90]}",
                    args={"prompt": sub["text"], "intent": sub["intent"], "mode": sub["mode"]},
                    depends_on=[prev_id] if prev_id else [],
                )
            )
            prev_id = sid
        plan = ExecutionPlan(plan_id=pid, goal=user_text[:120], complexity="multi_step", mode=decision.mode, steps=steps)
        validate_plan(plan, registry)
        return plan

    # Optional pre-tool step for deterministic intents (e.g. calculator on explicit arithmetic)
    tool_deps: list[str] = []
    if decision.intent == "math_calc" and registry.has("calculator"):
        expr = _extract_math_expression(user_text)
        if expr:
            steps.append(
                PlanStep(
                    step_id="calc-1",
                    action="tool",
                    description="Deterministik matematiksel hesaplama",
                    tool="calculator",
                    args={"expression": expr},
                )
            )
            tool_deps.append("calc-1")

    heavy_intents = {"project_build", "game_build", "research"}
    complexity = "distributed" if decision.intent in heavy_intents else ("multi_step" if tool_deps else "simple")
    action = "agent" if decision.intent in {"project_build", "game_build"} else "llm"
    steps.append(
        PlanStep(
            step_id="gen-1",
            action=action,
            description=f"{decision.intent} yanıt üretimi ({decision.mode})",
            args={"prompt": user_text, "intent": decision.intent, "mode": decision.mode},
            depends_on=tool_deps,
            capability="kod" if "code" in decision.intent or "project" in decision.intent else "genel",
        )
    )
    plan = ExecutionPlan(plan_id=pid, goal=user_text[:120], complexity=complexity, mode=decision.mode, steps=steps)
    validate_plan(plan, registry)
    return plan


def _extract_math_expression(text: str) -> str:
    import re

    m = re.search(r"([0-9][0-9\s\+\-\*/\(\)\.%]{2,}[0-9\)])", text or "")
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------- ORC-06 Parallel DAG Executor

@dataclass
class StepOutcome:
    step_id: str
    status: str  # ok | failed | skipped
    output: Any = None
    error: str = ""
    latency_ms: int = 0


class DAGExecutor:
    """ORC-06: Executes independent DAG steps in parallel while enforcing dependency order."""

    async def execute(
        self,
        plan: ExecutionPlan,
        registry: ToolRegistry,
        runner: Callable[[PlanStep, dict[str, StepOutcome]], Awaitable[Any]],
        *,
        on_event: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict[str, StepOutcome]:
        validate_plan(plan, registry)
        step_map = {s.step_id: s for s in plan.steps}
        pending = set(step_map.keys())
        results: dict[str, StepOutcome] = {}

        while pending:
            ready = [
                step_map[sid]
                for sid in sorted(pending)
                if all(dep in results for dep in step_map[sid].depends_on)
            ]
            if not ready:
                break

            async def _run_one(step: PlanStep) -> StepOutcome:
                failed_deps = [d for d in step.depends_on if results[d].status != "ok"]
                if failed_deps:
                    return StepOutcome(
                        step_id=step.step_id,
                        status="skipped",
                        error=f"Bağımlılık başarısız: {', '.join(failed_deps)}",
                    )
                if on_event:
                    await on_event("step_start", {"step_id": step.step_id, "description": step.description})
                t0 = time.perf_counter()
                last_err = ""
                for _attempt in range(max(1, step.retries)):
                    try:
                        out = await runner(step, results)
                        ms = int((time.perf_counter() - t0) * 1000)
                        outcome = StepOutcome(step_id=step.step_id, status="ok", output=out, latency_ms=ms)
                        if on_event:
                            await on_event("step_end", {"step_id": step.step_id, "status": "ok", "latency_ms": ms})
                        return outcome
                    except Exception as exc:
                        last_err = str(exc)
                ms = int((time.perf_counter() - t0) * 1000)
                outcome = StepOutcome(step_id=step.step_id, status="failed", error=last_err, latency_ms=ms)
                if on_event:
                    await on_event("step_end", {"step_id": step.step_id, "status": "failed", "error": last_err})
                return outcome

            wave = await asyncio.gather(*(_run_one(s) for s in ready))
            for out in wave:
                results[out.step_id] = out
                pending.discard(out.step_id)

        return results


# ---------------------------------------------------------------- ORC-07 Distributed Agent Dispatch

def select_online_agent(capability: str = "kod") -> dict[str, Any] | None:
    """ORC-07: Pick the highest-scoring online distributed agent using selection.py."""
    try:
        agents = db.list_agents()
    except Exception:
        return None
    online = [a for a in agents if a.get("status") in {"online", "idle", "ready"}]
    if not online:
        return None
    best = selection.pick_agent(online, task_type=capability) if hasattr(selection, "pick_agent") else online[0]
    return best or online[0]


async def dispatch_to_agent_or_local(
    *,
    prompt: str,
    capability: str,
    local_fallback: Callable[[], Awaitable[str]],
    poll_timeout_s: float = 2.0,
) -> dict[str, Any]:
    """ORC-07: Enqueue heavy task for an online distributed agent; cleanly fall back to local gateway."""
    agent = select_online_agent(capability)
    if not agent:
        text = await local_fallback()
        return {"source": "local_gateway", "agent_id": "master", "content": text, "fallback": True}

    task_id = f"orc-{uuid.uuid4().hex[:10]}"
    try:
        db.create_task(
            task_id=task_id,
            project_id="orchestrator",
            title=prompt[:80],
            description=prompt,
            task_type=capability,
            assigned_agent_id=agent["id"],
        )
    except Exception:
        text = await local_fallback()
        return {"source": "local_gateway", "agent_id": "master", "content": text, "fallback": True}

    deadline = time.monotonic() + poll_timeout_s
    while time.monotonic() < deadline:
        row = db.get_task(task_id)
        if row and row.get("status") == "completed" and row.get("result"):
            return {
                "source": "distributed_agent",
                "agent_id": agent["id"],
                "task_id": task_id,
                "content": str(row["result"]),
                "fallback": False,
            }
        await asyncio.sleep(0.1)

    # Graceful fallback if worker didn't claim within synchronous budget
    text = await local_fallback()
    return {
        "source": "local_gateway",
        "agent_id": "master",
        "task_id": task_id,
        "content": text,
        "fallback": True,
    }
