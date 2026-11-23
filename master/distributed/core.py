"""DIST-01..12, DIST-15..21: Agent Profiles, Benchmarks, Bandit Selection, Leases, Checkpoints, Map-Reduce, Merge & SLOs."""

from __future__ import annotations

import asyncio
import csv
import difflib
import io
import json
import random
import sqlite3
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

import config

AGENT_PROFILE_SCHEMA_VERSION = "2.0"

# DIST-05: Canonical mapping from all 30 orchestrator intents -> unified distributed task types
INTENT_TO_TASK_TYPE: dict[str, str] = {
    "greeting": "general", "chat": "general", "factual_qa": "research", "lesson": "documentation",
    "code_write": "backend", "code_only": "backend", "code_fix": "review", "project_build": "backend",
    "game_build": "frontend", "presentation": "documentation", "document_gen": "documentation",
    "research": "research", "data_analysis": "analysis", "image_gen": "media", "image_explain": "media",
    "audio_transcribe": "media", "translate": "general", "summarize": "documentation", "math_calc": "analysis",
    "legal_info": "domain_expert", "finance_dcf": "domain_expert", "health_info": "domain_expert",
    "cnc_engineering": "domain_expert", "file_convert": "general", "archive_zip": "general",
    "automation_mcp": "backend", "prompt_distill": "documentation", "cross_chat": "research",
    "short_answer": "general", "targeted_edit": "review",
}

TASK_TYPE_WEIGHTS: dict[str, dict[str, float]] = {
    "backend": {"coding": 0.50, "reasoning": 0.20, "context": 0.15, "structured": 0.10, "speed": 0.05},
    "frontend": {"coding": 0.45, "reasoning": 0.15, "context": 0.15, "structured": 0.15, "speed": 0.10},
    "testing": {"coding": 0.40, "reasoning": 0.25, "context": 0.15, "structured": 0.15, "speed": 0.05},
    "review": {"coding": 0.35, "reasoning": 0.35, "context": 0.20, "structured": 0.05, "speed": 0.05},
    "research": {"coding": 0.05, "reasoning": 0.35, "context": 0.35, "structured": 0.15, "speed": 0.10},
    "analysis": {"coding": 0.20, "reasoning": 0.40, "context": 0.20, "structured": 0.15, "speed": 0.05},
    "documentation": {"coding": 0.10, "reasoning": 0.25, "context": 0.35, "structured": 0.20, "speed": 0.10},
    "media": {"coding": 0.10, "reasoning": 0.20, "context": 0.25, "structured": 0.20, "speed": 0.25},
    "domain_expert": {"coding": 0.10, "reasoning": 0.45, "context": 0.25, "structured": 0.15, "speed": 0.05},
    "general": {"coding": 0.10, "reasoning": 0.30, "context": 0.20, "structured": 0.10, "speed": 0.30},
}


# ---------------------------------------------------------------- SQLite Persistence

def _dist_db_path() -> Path:
    p = Path(config.DATA_DIR) / "distributed.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _conn(db_path: Path | None = None) -> sqlite3.Connection:
    c = sqlite3.connect(str(db_path or _dist_db_path()), timeout=10.0)
    c.row_factory = sqlite3.Row
    return c


def init_distributed_db(db_path: Path | None = None) -> None:
    with _conn(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS agent_benchmark_history (
                run_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                model TEXT NOT NULL,
                scores_json TEXT NOT NULL,
                delta_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bandit_priors (
                task_type TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                alpha REAL NOT NULL DEFAULT 1.0,
                beta REAL NOT NULL DEFAULT 1.0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (task_type, agent_id)
            );
            CREATE TABLE IF NOT EXISTS task_leases (
                task_id TEXT PRIMARY KEY,
                assigned_agent TEXT NOT NULL,
                lease_version INTEGER NOT NULL DEFAULT 1,
                expires_at REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                result_etag TEXT NOT NULL DEFAULT '',
                result_payload TEXT NOT NULL DEFAULT '',
                late_results_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS task_checkpoints (
                task_id TEXT PRIMARY KEY,
                step_index INTEGER NOT NULL,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agent_perf_log (
                log_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                model TEXT NOT NULL,
                task_type TEXT NOT NULL,
                success INTEGER NOT NULL,
                tok_per_sec REAL NOT NULL DEFAULT 0.0,
                latency_ms INTEGER NOT NULL DEFAULT 0,
                retries INTEGER NOT NULL DEFAULT 0,
                hallucination_rate REAL NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL
            );
            """
        )


# ---------------------------------------------------------------- DIST-01 Versioned Agent Profile Schema

class HardwareSpec(BaseModel):
    gpu_name: str = "CPU-only"
    is_gpu: bool = False
    vram_gb: float = Field(0.0, ge=0.0)
    ram_gb: float = Field(8.0, ge=1.0)
    cpu_cores: int = Field(4, ge=1)


class BenchmarkScores(BaseModel):
    coding: float = Field(50.0, ge=0.0, le=100.0)
    reasoning: float = Field(50.0, ge=0.0, le=100.0)
    context: float = Field(50.0, ge=0.0, le=100.0)
    structured: float = Field(50.0, ge=0.0, le=100.0)
    speed: float = Field(50.0, ge=0.0, le=100.0)
    hallucination_rate: float = Field(0.05, ge=0.0, le=1.0)


class AgentProfile(BaseModel):
    schema_version: str = AGENT_PROFILE_SCHEMA_VERSION
    agent_id: str
    model: str
    param_billions: float = Field(4.0, gt=0.0)
    context_length: int = Field(8192, ge=1024)
    capabilities: list[str] = Field(default_factory=lambda: ["completion"])
    hardware: HardwareSpec = Field(default_factory=HardwareSpec)
    scores: BenchmarkScores = Field(default_factory=BenchmarkScores)
    warm_models: list[str] = Field(default_factory=list)
    active_load: int = Field(0, ge=0)
    queue_depth: int = Field(0, ge=0)


def validate_agent_profile(raw: dict[str, Any]) -> dict[str, Any]:
    """DIST-01: Validate versioned agent profile; warn (never reject) older schema versions."""
    warnings: list[str] = []
    ver = str(raw.get("schema_version") or "1.0")
    if ver != AGENT_PROFILE_SCHEMA_VERSION:
        warnings.append(f"Eski profil şeması ({ver}); {AGENT_PROFILE_SCHEMA_VERSION} sürümüne yükseltme önerilir.")
    try:
        prof = AgentProfile.model_validate({**raw, "schema_version": ver})
        return {"valid": True, "profile": prof, "warnings": warnings}
    except ValidationError as exc:
        return {"valid": False, "profile": None, "warnings": warnings, "errors": exc.errors()}


# ---------------------------------------------------------------- DIST-02 Deterministic 50-Task Benchmark Suite

BENCHMARK_DIMENSIONS = ("coding", "reasoning", "context", "structured", "speed")


def build_benchmark_tasks() -> list[dict[str, Any]]:
    """DIST-02: 50 deterministic tasks (10 per dimension) for repeatable agent evaluation."""
    tasks: list[dict[str, Any]] = []
    for dim in BENCHMARK_DIMENSIONS:
        for i in range(1, 11):
            tasks.append({"id": f"BM-{dim[:3].upper()}-{i:02d}", "dimension": dim, "prompt": f"{dim} değerlendirme görevi #{i}", "expected": f"ok-{i}"})
    return tasks


def record_benchmark_run(
    agent_id: str,
    model: str,
    scores: dict[str, float],
    *,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """DIST-02: Persist benchmark scores time-series and compute 'puan neden değişti' delta note."""
    init_distributed_db(db_path)
    with _conn(db_path) as conn:
        prev = conn.execute(
            "SELECT scores_json, model FROM agent_benchmark_history WHERE agent_id = ? ORDER BY created_at DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        delta_note = "İlk ölçüm kaydı."
        if prev:
            prev_sc = json.loads(prev["scores_json"])
            diffs = [f"{k}: {scores.get(k, 0) - prev_sc.get(k, 0):+.1f}" for k in BENCHMARK_DIMENSIONS if k in scores]
            reason = f"model değişti ({prev['model']} -> {model})" if prev["model"] != model else "periyodik yeniden değerlendirme"
            delta_note = f"{reason} | " + ", ".join(diffs)
        rid = f"bmr-{uuid.uuid4().hex[:10]}"
        now = datetime.now(UTC).isoformat()
        conn.execute(
            "INSERT INTO agent_benchmark_history (run_id, agent_id, model, scores_json, delta_note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (rid, agent_id, model, json.dumps(scores), delta_note, now),
        )
    return {"run_id": rid, "agent_id": agent_id, "scores": scores, "delta_note": delta_note}


# ---------------------------------------------------------------- DIST-04 Persistent Thompson Sampling Bandit Router

class ThompsonBanditRouter:
    """DIST-04: Persistent Beta(alpha, beta) Thompson Sampling router per (task_type, agent_id)."""

    def __init__(self, db_path: Path | None = None, *, enabled: bool = True, seed: int | None = None) -> None:
        self.db_path = db_path
        self.enabled = enabled
        self._rng = random.Random(seed)
        init_distributed_db(self.db_path)

    def get_prior(self, task_type: str, agent_id: str) -> tuple[float, float]:
        with _conn(self.db_path) as conn:
            row = conn.execute(
                "SELECT alpha, beta FROM bandit_priors WHERE task_type = ? AND agent_id = ?",
                (task_type, agent_id),
            ).fetchone()
        return (float(row["alpha"]), float(row["beta"])) if row else (1.0, 1.0)

    def record_outcome(self, task_type: str, agent_id: str, *, success: bool) -> tuple[float, float]:
        a, b = self.get_prior(task_type, agent_id)
        a_new, b_new = (a + 1.0, b) if success else (a, b + 1.0)
        with _conn(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO bandit_priors (task_type, agent_id, alpha, beta, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(task_type, agent_id) DO UPDATE SET alpha=excluded.alpha, beta=excluded.beta, updated_at=excluded.updated_at
                """,
                (task_type, agent_id, a_new, b_new, datetime.now(UTC).isoformat()),
            )
        return a_new, b_new

    def sample_score(self, task_type: str, agent_id: str) -> float:
        a, b = self.get_prior(task_type, agent_id)
        if not self.enabled:
            return a / (a + b)
        return self._rng.betavariate(a, b)


# ---------------------------------------------------------------- DIST-03 & DIST-12 Hardware-Aware Explainable Selection

def hardware_can_run_model(profile: AgentProfile, required_param_b: float) -> tuple[bool, str]:
    """DIST-12: Strictly prevent OOM by enforcing VRAM/RAM eligibility (e.g., 4 GB VRAM NEVER gets 9B task)."""
    est_vram_needed = required_param_b * 0.72  # Q4_K_M + KV cache baseline
    if profile.hardware.is_gpu:
        if profile.hardware.vram_gb < est_vram_needed:
            return False, f"VRAM yetersiz ({profile.hardware.vram_gb} GB < {est_vram_needed:.1f} GB gereken)"
        return True, "gpu_ok"
    if profile.hardware.ram_gb < est_vram_needed * 1.5:
        return False, f"CPU RAM yetersiz ({profile.hardware.ram_gb} GB)"
    return True, "cpu_ok"


def select_distributed_agent(
    agents: list[AgentProfile],
    *,
    task_type: str,
    required_param_b: float = 4.0,
    bandit: ThompsonBanditRouter | None = None,
) -> dict[str, Any]:
    """DIST-03, DIST-04, DIST-12: Score eligible agents with weights, warm bonus, bandit, hallucination penalty & explanation."""
    weights = TASK_TYPE_WEIGHTS.get(task_type, TASK_TYPE_WEIGHTS["general"])
    candidates: list[tuple[float, AgentProfile, str]] = []
    rejected: list[dict[str, str]] = []

    for ag in agents:
        ok, hw_reason = hardware_can_run_model(ag, required_param_b)
        if not ok:
            rejected.append({"agent_id": ag.agent_id, "reason": hw_reason})
            continue
        sc = ag.scores
        base = (
            weights["coding"] * sc.coding
            + weights["reasoning"] * sc.reasoning
            + weights["context"] * sc.context
            + weights["structured"] * sc.structured
            + weights["speed"] * sc.speed
        )
        warm_bonus = 6.0 if ag.model in ag.warm_models else 0.0
        bandit_bonus = (bandit.sample_score(task_type, ag.agent_id) * 12.0) if bandit else 0.0
        load_pen = ag.active_load * 4.5 + ag.queue_depth * 2.0
        hal_pen = sc.hallucination_rate * 25.0
        total = round(base + warm_bonus + bandit_bonus - load_pen - hal_pen, 3)
        reason = (
            f"{ag.agent_id} ({ag.model}) seçildi: {task_type} skoru={base:.1f}, "
            f"sıcak={warm_bonus:+.1f}, bandit={bandit_bonus:+.1f}, yük={-load_pen:.1f}, halüsinasyon={-hal_pen:.1f}"
        )
        candidates.append((total, ag, reason))

    if not candidates:
        return {"selected": None, "reason": "Donanım/VRAM gereksinimini karşılayan uygun ajan yok.", "rejected": rejected}

    candidates.sort(key=lambda t: t[0], reverse=True)
    best_score, best_ag, best_reason = candidates[0]
    return {
        "selected": best_ag.agent_id,
        "model": best_ag.model,
        "score": best_score,
        "reason": best_reason,
        "rejected": rejected,
    }


# ---------------------------------------------------------------- DIST-06 Idempotent Leases & DIST-08 Checkpoints

def acquire_task_lease(task_id: str, agent_id: str, *, ttl_s: float = 120.0, db_path: Path | None = None) -> dict[str, Any]:
    init_distributed_db(db_path)
    with _conn(db_path) as conn:
        cur = conn.execute("SELECT lease_version FROM task_leases WHERE task_id = ?", (task_id,)).fetchone()
        new_ver = (int(cur["lease_version"]) + 1) if cur else 1
        exp = time.time() + ttl_s
        conn.execute(
            """
            INSERT INTO task_leases (task_id, assigned_agent, lease_version, expires_at, status)
            VALUES (?, ?, ?, ?, 'active')
            ON CONFLICT(task_id) DO UPDATE SET
                assigned_agent=excluded.assigned_agent,
                lease_version=excluded.lease_version,
                expires_at=excluded.expires_at,
                status='active'
            """,
            (task_id, agent_id, new_ver, exp),
        )
    return {"task_id": task_id, "assigned_agent": agent_id, "lease_version": new_ver, "expires_at": exp}


def submit_idempotent_result(
    task_id: str,
    agent_id: str,
    *,
    lease_version: int,
    etag: str,
    payload: str,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """DIST-06 & DIST-07: Enforce ownership, idempotency via ETag, and protect active leases against late stale results."""
    init_distributed_db(db_path)
    with _conn(db_path) as conn:
        row = conn.execute("SELECT * FROM task_leases WHERE task_id = ?", (task_id,)).fetchone()
        if not row:
            raise KeyError(f"Görev kiralaması bulunamadı: {task_id}")
        if row["status"] == "done" and row["result_etag"] == etag:
            return {"status": "idempotent_replay", "accepted": True, "payload": row["result_payload"]}
        if int(row["lease_version"]) != lease_version or row["assigned_agent"] != agent_id or time.time() > float(row["expires_at"]):
            late = json.loads(row["late_results_json"] or "[]")
            late.append({"agent_id": agent_id, "lease_version": lease_version, "etag": etag, "at": datetime.now(UTC).isoformat()})
            conn.execute("UPDATE task_leases SET late_results_json = ? WHERE task_id = ?", (json.dumps(late), task_id))
            return {"status": "rejected_stale_or_unauthorized", "accepted": False, "active_agent": row["assigned_agent"]}
        conn.execute(
            "UPDATE task_leases SET status = 'done', result_etag = ?, result_payload = ? WHERE task_id = ?",
            (etag, payload, task_id),
        )
    return {"status": "accepted", "accepted": True, "payload": payload}


def save_checkpoint(task_id: str, step_index: int, state: dict[str, Any], *, max_bytes: int = 256_000, db_path: Path | None = None) -> dict[str, Any]:
    """DIST-08: Persist bounded step checkpoint so another agent resumes cleanly after node failure."""
    init_distributed_db(db_path)
    blob = json.dumps(state, ensure_ascii=False)
    if len(blob.encode("utf-8")) > max_bytes:
        raise ValueError("Checkpoint boyut sınırını aşıyor.")
    now = datetime.now(UTC).isoformat()
    with _conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO task_checkpoints (task_id, step_index, state_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET step_index=excluded.step_index, state_json=excluded.state_json, updated_at=excluded.updated_at
            """,
            (task_id, int(step_index), blob, now),
        )
    return {"task_id": task_id, "step_index": int(step_index), "saved_at": now}


def load_checkpoint(task_id: str, *, db_path: Path | None = None) -> dict[str, Any] | None:
    init_distributed_db(db_path)
    with _conn(db_path) as conn:
        row = conn.execute("SELECT * FROM task_checkpoints WHERE task_id = ?", (task_id,)).fetchone()
    if not row:
        return None
    return {"task_id": row["task_id"], "step_index": int(row["step_index"]), "state": json.loads(row["state_json"])}


# ---------------------------------------------------------------- DIST-09 Map-Reduce & DIST-10 Work Stealing

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
            except Exception as exc:
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
    return {"total_shards": len(shards), "succeeded": len(results), "failed_shards": failed_indices, "retries_used": retries_used, "reduced": reduced}


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


# ---------------------------------------------------------------- DIST-15 3-Way Merge, DIST-16 Review, DIST-17 Test, DIST-18 Escalation

def three_way_merge(base: str, ours: str, theirs: str) -> dict[str, Any]:
    """DIST-15: Automatic 3-way line merge; resolves non-overlapping edits and flags exact conflict hunks."""
    b_lines = base.splitlines()
    o_lines = ours.splitlines()
    t_lines = theirs.splitlines()
    if o_lines == b_lines:
        return {"auto_merged": True, "merged": theirs, "conflicts": []}
    if t_lines == b_lines or o_lines == t_lines:
        return {"auto_merged": True, "merged": ours, "conflicts": []}

    # Compute per-line change maps relative to base
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
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=str(workspace_dir),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
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


# ---------------------------------------------------------------- DIST-19 Performance Matrix, DIST-20 Provenance, DIST-21 Amdahl Speedup

def log_agent_performance(
    *,
    agent_id: str,
    model: str,
    task_type: str,
    success: bool,
    tok_per_sec: float,
    latency_ms: int,
    retries: int = 0,
    hallucination_rate: float = 0.0,
    db_path: Path | None = None,
) -> str:
    init_distributed_db(db_path)
    lid = f"plg-{uuid.uuid4().hex[:10]}"
    with _conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO agent_perf_log
                (log_id, agent_id, model, task_type, success, tok_per_sec, latency_ms, retries, hallucination_rate, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (lid, agent_id, model, task_type, int(success), float(tok_per_sec), int(latency_ms), int(retries), float(hallucination_rate), datetime.now(UTC).isoformat()),
        )
    return lid


def build_performance_matrix(db_path: Path | None = None) -> dict[str, Any]:
    """DIST-19: Aggregate agent x task_type matrix + CSV export for academic reporting."""
    init_distributed_db(db_path)
    with _conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT agent_id, model, task_type,
                   COUNT(*) AS runs,
                   AVG(success) AS success_rate,
                   AVG(tok_per_sec) AS avg_tok_s,
                   AVG(latency_ms) AS avg_latency_ms,
                   SUM(retries) AS total_retries,
                   AVG(hallucination_rate) AS avg_hal_rate
            FROM agent_perf_log
            GROUP BY agent_id, model, task_type
            ORDER BY success_rate DESC
            """
        ).fetchall()
    matrix = [
        {
            "agent_id": r["agent_id"],
            "model": r["model"],
            "task_type": r["task_type"],
            "runs": int(r["runs"]),
            "success_rate": round(float(r["success_rate"]), 4),
            "avg_tok_s": round(float(r["avg_tok_s"]), 2),
            "avg_latency_ms": round(float(r["avg_latency_ms"]), 1),
            "total_retries": int(r["total_retries"]),
            "avg_hal_rate": round(float(r["avg_hal_rate"]), 4),
        }
        for r in rows
    ]
    buf = io.StringIO()
    cols = ["agent_id", "model", "task_type", "runs", "success_rate", "avg_tok_s", "avg_latency_ms", "total_retries", "avg_hal_rate"]
    writer = csv.DictWriter(buf, fieldnames=cols)
    writer.writeheader()
    writer.writerows(matrix)
    return {"rows": matrix, "csv": buf.getvalue()}


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
