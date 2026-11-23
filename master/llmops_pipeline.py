"""Cluster C ([M43]..[M45]): Continuous Active Learning & Local LLMOps Pipeline.

Captures user corrections and feedback as validated Direct Preference Optimization (DPO)
triples in ``config.DATA_DIR / "dpo_preferences.jsonl"``, tracks domain readiness metrics
for nightly QLoRA/DPO fine-tuning, and enforces a paired statistical promotion gate
before rolling out candidate GGUF models.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import config

NIGHTLY_QLORA_MIN_PAIRS = 25


def _data_dir() -> Path:
    base = Path(getattr(config, "DATA_DIR", Path(config.DB_PATH).parent))
    base.mkdir(parents=True, exist_ok=True)
    return base


def _dpo_file_path() -> Path:
    return _data_dir() / "dpo_preferences.jsonl"


def record_dpo_preference(
    prompt: str,
    chosen: str,
    rejected: str,
    domain: str = "general",
) -> dict[str, Any]:
    """Validate and append a DPO preference triple to ``config.DATA_DIR / "dpo_preferences.jsonl"``."""
    clean_prompt = (prompt or "").strip()
    clean_chosen = (chosen or "").strip()
    clean_rejected = (rejected or "").strip()
    clean_domain = (domain or "general").strip().lower() or "general"

    if not clean_prompt:
        raise ValueError("prompt must not be empty")
    if not clean_chosen:
        raise ValueError("chosen response must not be empty")
    if not clean_rejected:
        raise ValueError("rejected response must not be empty")
    if clean_chosen == clean_rejected:
        raise ValueError("chosen and rejected responses must be distinct for DPO training")

    digest_input = f"{clean_domain}||{clean_prompt}||{clean_chosen}||{clean_rejected}"
    record_id = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:16]

    record: dict[str, Any] = {
        "id": record_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "domain": clean_domain,
        "prompt": clean_prompt,
        "chosen": clean_chosen,
        "rejected": clean_rejected,
        "chosen_chars": len(clean_chosen),
        "rejected_chars": len(clean_rejected),
    }

    target_file = _dpo_file_path()
    with target_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record


def evaluate_model_gate(
    baseline_scores: list[float],
    candidate_scores: list[float],
    min_delta: float = 0.01,
    alpha_level: float = 0.05,
) -> dict[str, Any]:
    """Compare candidate vs baseline benchmark scores using a paired t-statistic normal approximation.

    Promotes the candidate model only if ``mean(candidate) - mean(baseline) >= min_delta``
    and the one-sided p-value approximation is below ``alpha_level`` (or variance is zero
    with positive delta).
    """
    if not baseline_scores or not candidate_scores:
        raise ValueError("baseline_scores and candidate_scores must be non-empty")
    if len(baseline_scores) != len(candidate_scores):
        raise ValueError("baseline_scores and candidate_scores must have equal length")

    n = len(baseline_scores)
    b_vals = [float(x) for x in baseline_scores]
    c_vals = [float(x) for x in candidate_scores]
    diffs = [c - b for b, c in zip(b_vals, c_vals, strict=True)]

    mean_base = sum(b_vals) / n
    mean_cand = sum(c_vals) / n
    delta = mean_cand - mean_base

    if n == 1:
        p_val = 0.01 if delta >= min_delta else 1.0
        t_stat = float("inf") if delta > 0 else 0.0
    else:
        variance = sum((d - delta) ** 2 for d in diffs) / (n - 1)
        std_diff = math.sqrt(max(0.0, variance))
        se = std_diff / math.sqrt(n)
        if se <= 1e-12:
            t_stat = 99.0 if delta > 0 else (-99.0 if delta < 0 else 0.0)
            p_val = 0.0001 if delta > 0 else 1.0
        else:
            t_stat = delta / se
            # Upper-tail normal complementary error function approximation
            p_val = 0.5 * math.erfc(t_stat / math.sqrt(2.0))

    wins = sum(1 for d in diffs if d > 1e-9)
    losses = sum(1 for d in diffs if d < -1e-9)
    ties = n - wins - losses

    promote = bool(delta >= min_delta and p_val <= alpha_level and losses <= wins)

    return {
        "promote": promote,
        "sample_size": n,
        "baseline_mean": round(mean_base, 5),
        "candidate_mean": round(mean_cand, 5),
        "delta": round(delta, 5),
        "t_stat": round(t_stat, 4),
        "p_value_approx": round(float(p_val), 6),
        "wins": wins,
        "losses": losses,
        "ties": ties,
    }


def get_llmops_stats(min_pairs_threshold: int = NIGHTLY_QLORA_MIN_PAIRS) -> dict[str, Any]:
    """Summarize collected DPO preference records by domain and report nightly QLoRA readiness."""
    target_file = _dpo_file_path()
    by_domain: dict[str, int] = {}
    total_pairs = 0
    latest_timestamp = ""

    if target_file.exists():
        for raw_line in target_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if not isinstance(item, dict):
                continue
            dom = str(item.get("domain") or "general").strip().lower() or "general"
            by_domain[dom] = by_domain.get(dom, 0) + 1
            total_pairs += 1
            ts = str(item.get("timestamp") or "")
            if ts > latest_timestamp:
                latest_timestamp = ts

    threshold = max(1, int(min_pairs_threshold))
    ready_domains = sorted(dom for dom, count in by_domain.items() if count >= threshold)

    return {
        "dpo_file": str(target_file),
        "total_pairs": total_pairs,
        "by_domain": by_domain,
        "min_pairs_threshold": threshold,
        "ready_for_nightly_qlora": total_pairs >= threshold,
        "ready_domains": ready_domains,
        "remaining_to_threshold": max(0, threshold - total_pairs),
        "latest_timestamp": latest_timestamp,
    }
