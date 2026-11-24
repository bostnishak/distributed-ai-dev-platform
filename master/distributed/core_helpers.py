"""Pure helpers for distributed execution: seeded Beta sampling, map-reduce, work-stealing, 3-way merge, test runner & SLOs."""

from __future__ import annotations

import asyncio
import difflib
import hashlib
import math
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from process_utils import run_process


class SeededBetaSampler:
    """Deterministic Beta(alpha, beta) sampler backed by SHA-256 counter mode."""

    def __init__(self, seed: int) -> None:
        self._seed = str(seed).encode("utf-8")
        self._counter = 0

    def _uniform(self) -> float:
        self._counter += 1
        digest = hashlib.sha256(self._seed + self._counter.to_bytes(8, "big")).digest()
        val = int.from_bytes(digest[:8], "big") / float(1 << 64)
        return min(max(val, 1e-12), 1.0 - 1e-12)

    def _normal(self) -> float:
        u1 = self._uniform()
        u2 = self._uniform()
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

    def _gamma(self, shape: float) -> float:
        if shape < 1.0:
            return self._gamma(shape + 1.0) * (self._uniform() ** (1.0 / shape))
        d = shape - 1.0 / 3.0
        c = 1.0 / math.sqrt(9.0 * d)
        while True:
            x = self._normal()
            v = 1.0 + c * x
            if v <= 0.0:
                continue
            v3 = v * v * v
            u = self._uniform()
            if u < 1.0 - 0.0331 * (x**4) or math.log(u) < 0.5 * x * x + d * (1.0 - v3 + math.log(v3)):
                return d * v3

    def betavariate(self, alpha: float, beta: float) -> float:
        x = self._gamma(max(1e-4, float(alpha)))
        y = self._gamma(max(1e-4, float(beta)))
        return x / (x + y) if (x + y) > 0.0 else 0.5


async def map_reduce_distributed(
    shards: list[Any],
    map_fn,
    reduce_fn,
    *,
    max_retries: int = 2,
) -> dict[str, Any]:
    """DIST-09: Parallel map across agents; on partial failure retry ONLY failed shards, then reduce."""
    results: dict[int, Any] = {}
    failed_indices = list(range(len(shards)))
    retries_used = 0

    for attempt in range(max_retries + 1):
        if not failed_indices:
            break
        if attempt > 0:
            retries_used += 1

        async def _run(idx: int) -> tuple[int, bool, Any]:
            try:
                out = await map_fn(idx, shards[idx])
                return idx, True, out
            except (
                OSError,
                RuntimeError,
                ValueError,
                TypeError,
                LookupError,
                ArithmeticError,
                AttributeError,
                sqlite3.Error,
                subprocess.SubprocessError,
            ) as exc:
                return idx, False, str(exc)

        wave = await asyncio.gather(*(_run(i) for i in failed_indices))
        next_failed: list[int] = []
        for idx, ok, val in wave:
            if ok:
                results[idx] = val
            else:
                next_failed.append(idx)
        failed_indices = next_failed

    ordered = [results[i] for i in sorted(results)]
    reduced = reduce_fn(ordered)
    return {
        "total_shards": len(shards),
        "succeeded": len(results),
        "failed_shards": failed_indices,
        "retries_used": retries_used,
        "reduced": reduced,
    }


def steal_work_if_imbalanced(queues: dict[str, list[str]], idle_agent: str) -> dict[str, Any]:
    """DIST-10: Idle agent steals one pending task from the longest queue."""
    if queues.get(idle_agent):
        return {"stolen": False, "reason": "Ajan zaten meşgul."}
    busiest = max(queues.items(), key=lambda kv: len(kv[1]), default=("", []))
    donor_id, donor_q = busiest
    if not donor_id or donor_id == idle_agent or len(donor_q) < 2:
        return {"stolen": False, "reason": "Çalınacak dengesiz kuyruk yok."}
    stolen_task = donor_q.pop()
    queues.setdefault(idle_agent, []).append(stolen_task)
    return {"stolen": True, "task_id": stolen_task, "from_agent": donor_id, "to_agent": idle_agent}


def three_way_merge(base: str, ours: str, theirs: str) -> dict[str, Any]:
    """DIST-15: Automatic 3-way line merge; resolves non-overlapping edits and flags exact conflict hunks."""
    b_lines = base.splitlines()
    o_lines = ours.splitlines()
    t_lines = theirs.splitlines()
    if o_lines == b_lines:
        return {"auto_merged": True, "merged": theirs, "conflicts": []}
    if t_lines == b_lines or o_lines == t_lines:
        return {"auto_merged": True, "merged": ours, "conflicts": []}

    o_sm = difflib.SequenceMatcher(None, b_lines, o_lines)
    t_sm = difflib.SequenceMatcher(None, b_lines, t_lines)
    o_edits = {i1: (i2, o_lines[j1:j2]) for tag, i1, i2, j1, j2 in o_sm.get_opcodes() if tag != "equal"}
    t_edits = {i1: (i2, t_lines[j1:j2]) for tag, i1, i2, j1, j2 in t_sm.get_opcodes() if tag != "equal"}

    overlap = set(o_edits) & set(t_edits)
    if overlap:
        conflicts = [
            {"line": ln + 1, "ours": "\n".join(o_edits[ln][1]), "theirs": "\n".join(t_edits[ln][1])}
            for ln in sorted(overlap)
        ]
        return {"auto_merged": False, "merged": "", "conflicts": conflicts}

    merged: list[str] = []
    i = 0
    while i < len(b_lines):
        if i in o_edits:
            i2, rep = o_edits[i]
            merged.extend(rep)
            i = max(i + 1, i2)
        elif i in t_edits:
            i2, rep = t_edits[i]
            merged.extend(rep)
            i = max(i + 1, i2)
        else:
            merged.append(b_lines[i])
            i += 1
    return {"auto_merged": True, "merged": "\n".join(merged), "conflicts": []}


def execute_test_agent_task(workspace_dir: Path) -> dict[str, Any]:
    """DIST-17: Run actual pytest on generated workspace; reopen code task automatically if tests fail."""
    proc = run_process([sys.executable, "-m", "pytest", "-q"], cwd=workspace_dir, timeout_s=30.0)
    passed = proc.returncode == 0
    return {
        "passed": passed,
        "reopen_code_task": not passed,
        "stdout": (proc.stdout + "\n" + proc.stderr).strip()[:600],
    }


def decide_failure_recovery(attempt: int, error_class: str, current_agent: str) -> dict[str, Any]:
    """DIST-18: Escalating recovery policy (1: same agent -> 2: different agent -> 3: stronger/council -> 4: human)."""
    if attempt <= 1 and error_class in {"connection", "timeout"}:
        return {"action": "retry_same_agent", "target": current_agent, "error_class": error_class}
    if attempt <= 2:
        return {"action": "reassign_different_agent", "exclude": current_agent, "error_class": error_class}
    if attempt == 3:
        return {"action": "escalate_stronger_or_council", "error_class": error_class}
    return {
        "action": "escalate_human",
        "error_class": error_class,
        "summary": f"Görev 3 kurtarma denemesinden sonra '{error_class}' hatasıyla başarısız oldu; insan müdahalesi gerekir.",
    }


def build_project_provenance(files_meta: list[dict[str, Any]]) -> dict[str, Any]:
    """DIST-20: Build PROVENANCE.json mapping every produced file to task, agent, model & verification status."""
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "files": [
            {
                "file": m["file"],
                "task_id": m.get("task_id", ""),
                "performed_by": m.get("agent_id", "master"),
                "model": m.get("model", ""),
                "prompt_summary": str(m.get("prompt_summary") or "")[:140],
                "verified": bool(m.get("verified", True)),
            }
            for m in files_meta
        ],
    }


def compute_amdahl_speedup(serial_fraction: float, agent_counts: tuple[int, ...] = (1, 2, 4, 6)) -> list[dict[str, float]]:
    """DIST-21: Amdahl speedup & parallel efficiency table across 1/2/4/6 distributed agents."""
    s = max(0.0, min(1.0, float(serial_fraction)))
    out: list[dict[str, float]] = []
    for n in agent_counts:
        speedup = 1.0 / (s + (1.0 - s) / max(1, n))
        out.append({"agents": n, "speedup": round(speedup, 3), "efficiency": round(speedup / n, 3)})
    return out
