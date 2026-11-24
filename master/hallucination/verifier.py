"""HAL-01, HAL-06..HAL-26, HAL-28: Claim Verification, NLI Entailment, Numeric/Code/Premise/High-Risk Guardrails & Telemetry."""

from __future__ import annotations

import re
import sqlite3
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import config
from hallucination.verifier_checks import (
    apply_high_risk_guardrails,
    audit_python_code_apis,
    compute_confidence,
    datetime_tool,
    decide_abstention,
    detect_false_premise,
    detect_unanswerable,
    guard_memory_write,
    verify_numbers_and_tables,
    verify_presentation_sources,
    verify_standard_and_law_numbers,
)
from prompt_loader import load_prompt
from rag.store import normalize_turkish_text, tr_lower

__all__ = [
    "HALLUCINATION_TAXONOMY",
    "Claim",
    "ClaimVerification",
    "apply_high_risk_guardrails",
    "approve_wrong_answer_report",
    "audit_python_code_apis",
    "chain_of_verification",
    "check_chat_consistency",
    "compute_confidence",
    "datetime_tool",
    "decide_abstention",
    "detect_false_premise",
    "detect_unanswerable",
    "enforce_citation_policy",
    "extract_claims",
    "get_model_hallucination_profiles",
    "guard_memory_write",
    "init_hallucination_db",
    "list_approved_corrections",
    "log_verification_telemetry",
    "nli_score_pair",
    "self_consistency_check",
    "submit_wrong_answer_report",
    "telemetry_summary_7d",
    "update_model_hallucination_profile",
    "verify_claims_nli",
    "verify_numbers_and_tables",
    "verify_presentation_sources",
    "verify_standard_and_law_numbers",
]

# HAL-01: Canonical Hallucination Taxonomy
HALLUCINATION_TAXONOMY: dict[str, dict[str, str]] = {
    "fabricated_fact": {
        "name": "Uydurma olgu",
        "detector": "HAL-07 NLI claim-source entailment + HAL-15 abstention",
        "owner": "rag+hallucination",
    },
    "fabricated_citation": {
        "name": "Uydurma kaynak/atıf",
        "detector": "RAG-11 citation resolver + RAG-21 DOI check",
        "owner": "rag",
    },
    "numeric_error": {
        "name": "Yanlış sayı/hesap",
        "detector": "HAL-09 numeric provenance + ORC-08 calculator",
        "owner": "hallucination+orchestrator",
    },
    "fabricated_code_api": {
        "name": "Uydurma kod API'si",
        "detector": "HAL-12 sandbox exec + HAL-13 AST import/signature audit",
        "owner": "hallucination+sandbox",
    },
    "out_of_context": {
        "name": "Bağlam dışı bilgi",
        "detector": "RAG-08 relevance threshold + HAL-22 strict grounding",
        "owner": "rag+hallucination",
    },
    "instruction_violation": {
        "name": "Talimat ihlali",
        "detector": "MODE-01..08 programmatic contract + HAL-20 validator",
        "owner": "orchestrator",
    },
    "self_contradiction": {
        "name": "Kendi kendine çelişki",
        "detector": "HAL-21 chat consistency NLI check",
        "owner": "hallucination",
    },
    "overconfidence": {
        "name": "Aşırı özgüven",
        "detector": "HAL-14 calibrated confidence + ML-03 calibrator",
        "owner": "hallucination+ml_ops",
    },
}

_FENCE_RE = re.compile(r"```[\s\S]*?```")
_OPINION_PREFIX_RE = re.compile(r"^\s*(?:bence|bana\s+göre|kanımca|i\s+think|in\s+my\s+opinion|tercihen)\b", re.IGNORECASE)
_NUM_RE = re.compile(r"\b\d+(?:[.,]\d+)?%?\b")
_DATE_RE = re.compile(r"\b(?:1[0-9]{3}|20[0-9]{2})\b")
_CITE_TAG_RE = re.compile(r"\[S(\d+)\]")
_STD_LAW_RE = re.compile(
    r"\b(?:ISO\s*\d{3,5}(?:-\d+)?|DIN\s*\d{3,5}|TS\s*\d{3,5}|TCK\s*m\.\s*\d+|TBK\s*m\.\s*\d+|KVKK\s*m\.\s*\d+|Madde\s*\d+)\b",
    re.IGNORECASE,
)
_NEGATION_TOKENS = frozenset({"değil", "değildir", "yok", "yoktur", "hiç", "olmayan", "yasak", "not", "never", "no", "cannot", "false"})


@dataclass
class Claim:
    text: str
    claim_type: str  # fact | number | date | entity | citation | code_api
    span: tuple[int, int]
    cited_ids: list[str] = field(default_factory=list)


@dataclass
class ClaimVerification:
    claim: Claim
    status: str  # supported | unsupported | contradicted | no_source
    support_score: float
    matched_source_id: str = ""
    reason: str = ""


# ---------------------------------------------------------------- HAL-06 Claim Extraction

def extract_claims(text: str) -> list[Claim]:
    """HAL-06: Extract atomic verifiable claims excluding code blocks and explicit opinions."""
    scrubbed = _FENCE_RE.sub(" ", text or "")
    claims: list[Claim] = []
    pos = 0
    for seg in re.split(r"(?<=[.!?])\s+|\n+", scrubbed):
        s = seg.strip()
        start = (text or "").find(s, pos) if s else pos
        end = start + len(s)
        pos = max(pos, end)
        if len(s) < 12 or _OPINION_PREFIX_RE.match(s) or s.startswith("#"):
            continue
        cited = [f"S{m}" for m in _CITE_TAG_RE.findall(s)]
        if _STD_LAW_RE.search(s):
            ctype = "entity"
        elif _NUM_RE.search(s):
            ctype = "number"
        elif _DATE_RE.search(s):
            ctype = "date"
        elif cited:
            ctype = "citation"
        else:
            ctype = "fact"
        claims.append(Claim(text=s, claim_type=ctype, span=(max(0, start), end), cited_ids=cited))
    return claims


# ---------------------------------------------------------------- HAL-07 NLI Claim-Source Entailment

def nli_score_pair(claim_text: str, premise_text: str) -> tuple[str, float]:
    """Lightweight calibrated NLI (entailment / neutral / contradiction) for Turkish & English."""
    c_norm = normalize_turkish_text(claim_text).split()
    p_norm = normalize_turkish_text(premise_text).split()
    c_set = {t for t in c_norm if len(t) >= 3}
    p_set = {t for t in p_norm if len(t) >= 3}
    if not c_set or not p_set:
        return "neutral", 0.0

    overlap = len(c_set & p_set) / max(1, len(c_set))
    c_nums = set(_NUM_RE.findall(claim_text))
    p_nums = set(_NUM_RE.findall(premise_text))
    c_neg = bool(set(re.findall(r"[a-zA-Zçğıöşü]+", tr_lower(claim_text))) & _NEGATION_TOKENS)
    p_neg = bool(set(re.findall(r"[a-zA-Zçğıöşü]+", tr_lower(premise_text))) & _NEGATION_TOKENS)

    if overlap >= 0.35 and c_nums and p_nums and bool(c_nums - p_nums):
        return "contradiction", round(overlap, 3)
    if overlap >= 0.45 and c_neg != p_neg:
        return "contradiction", round(overlap, 3)
    if overlap >= 0.40 and (not c_nums or not (c_nums - p_nums)):
        return "entailment", round(min(0.99, overlap + 0.25), 3)
    return "neutral", round(overlap, 3)


def verify_claims_nli(claims: list[Claim], sources: list[dict[str, Any]]) -> list[ClaimVerification]:
    """HAL-07: Match every atomic claim against retrieved sources using NLI scoring."""
    if not sources:
        return [ClaimVerification(claim=c, status="no_source", support_score=0.0, reason="Kaynak yok") for c in claims]

    valid_ids = {str(s.get("id") or f"S{i + 1}") for i, s in enumerate(sources)}
    results: list[ClaimVerification] = []
    for cl in claims:
        bad_cites = [cid for cid in cl.cited_ids if cid not in valid_ids]
        if bad_cites:
            results.append(
                ClaimVerification(
                    claim=cl,
                    status="unsupported",
                    support_score=0.0,
                    reason=f"Olmayan kaynak etiketi: {', '.join(bad_cites)}",
                )
            )
            continue

        best_status = "unsupported"
        best_score = 0.0
        best_sid = ""
        for idx, src in enumerate(sources):
            sid = str(src.get("id") or f"S{idx + 1}")
            txt = str(src.get("content") or src.get("quote") or "")
            label, sc = nli_score_pair(cl.text, txt)
            if label == "contradiction" and sc >= best_score:
                best_status, best_score, best_sid = "contradicted", sc, sid
            elif label == "entailment" and best_status != "contradicted" and sc > best_score:
                best_status, best_score, best_sid = "supported", sc, sid
        results.append(ClaimVerification(claim=cl, status=best_status, support_score=best_score, matched_source_id=best_sid))
    return results


# ---------------------------------------------------------------- HAL-08 Citation Enforcement & Repair

def enforce_citation_policy(
    text: str,
    sources: list[dict[str, Any]],
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """HAL-08 & HAL-22: Remove contradicted claims, flag or strip unsupported claims, and re-verify."""
    claims = extract_claims(text)
    verifs = verify_claims_nli(claims, sources)
    kept_lines: list[str] = []
    removed: list[str] = []
    flagged: list[str] = []

    for v in verifs:
        if v.status == "supported":
            s = v.claim.text
            if v.matched_source_id and f"[{v.matched_source_id}]" not in s:
                s = f"{s} [{v.matched_source_id}]"
            kept_lines.append(s)
        elif v.status == "contradicted" or strict:
            removed.append(v.claim.text)
        else:
            flagged.append(v.claim.text)
            kept_lines.append(f"{v.claim.text} [doğrulanamadı]")

    if strict and not kept_lines:
        repaired = "İstenen bilgi verilen belgede bulunmuyor."
    else:
        repaired = " ".join(kept_lines).strip() or text

    total = max(1, len(verifs))
    supported_count = sum(1 for v in verifs if v.status == "supported")
    return {
        "repaired_text": repaired,
        "support_ratio": round(supported_count / total, 4),
        "supported": supported_count,
        "total_claims": len(verifs),
        "removed_claims": removed,
        "flagged_claims": flagged,
        "verifications": [
            {"text": v.claim.text, "status": v.status, "score": v.support_score, "source": v.matched_source_id}
            for v in verifs
        ],
    }


# ---------------------------------------------------------------- HAL-10 Chain-of-Verification, HAL-11 Self-Consistency & HAL-21 Chat Consistency

async def chain_of_verification(
    draft: str,
    sources: list[dict[str, Any]],
    *,
    answer_question_fn=None,
) -> dict[str, Any]:
    """HAL-10: Generate independent verification questions from claims, check against sources, and revise."""
    claims = extract_claims(draft)
    questions = [f"Şu iddia kaynaklarla doğrulanıyor mu: '{c.text}'?" for c in claims[:5]]
    findings: list[dict[str, Any]] = []
    for cl, q in zip(claims[:5], questions, strict=False):
        ver = verify_claims_nli([cl], sources)[0]
        if answer_question_fn is not None:
            ind_ans = await answer_question_fn(q, sources)
            findings.append({"question": q, "independent_answer": ind_ans, "status": ver.status})
        else:
            findings.append({"question": q, "status": ver.status, "source": ver.matched_source_id})
    enforced = enforce_citation_policy(draft, sources, strict=False)
    return {"questions": questions, "findings": findings, "revised_text": enforced["repaired_text"]}


def self_consistency_check(samples: list[str]) -> dict[str, Any]:
    """HAL-11: Majority vote and agreement ratio across n=3..5 independent answer samples."""
    cleaned = [re.sub(r"\s+", " ", (s or "").strip().lower()) for s in samples if (s or "").strip()]
    if not cleaned:
        return {"majority_answer": "", "agreement": 0.0, "consistent": False}
    counts = Counter(cleaned)
    top_ans, top_n = counts.most_common(1)[0]
    agreement = round(top_n / len(cleaned), 4)
    return {
        "majority_answer": top_ans,
        "agreement": agreement,
        "consistent": agreement >= 0.6,
        "sample_count": len(cleaned),
    }


def check_chat_consistency(new_text: str, prior_verified_statements: list[str]) -> dict[str, Any]:
    """HAL-21: Check whether new response claims contradict earlier verified statements in the same chat."""
    new_claims = extract_claims(new_text)
    contradictions: list[dict[str, str]] = []
    for cl in new_claims:
        for prev in prior_verified_statements:
            label, sc = nli_score_pair(cl.text, prev)
            if label == "contradiction" and sc >= 0.4:
                contradictions.append({"new_claim": cl.text, "prior_statement": prev})
    return {"consistent": len(contradictions) == 0, "contradictions": contradictions}


# ---------------------------------------------------------------- HAL-25 Wrong-Answer Queue, HAL-26 Telemetry, HAL-28 Model Profiles

def _hal_db_path() -> Path:
    p = Path(config.DATA_DIR) / "hallucination.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _hal_conn() -> sqlite3.Connection:
    import dbconn

    return dbconn.open_db(_hal_db_path())


def init_hallucination_db() -> None:
    with _hal_conn() as conn:
        conn.executescript(load_prompt("b3_hallucination_schema.txt"))


def log_verification_telemetry(
    *,
    run_id: str,
    model: str,
    task_type: str,
    **metrics: Any,
) -> str:
    """HAL-26: Persist verification metrics (support_ratio, citation_coverage, confidence, abstained, verify_ms)."""
    init_hallucination_db()
    eid = f"ht-{uuid.uuid4().hex[:10]}"
    support_ratio = float(metrics["support_ratio"])
    citation_coverage = float(metrics["citation_coverage"])
    confidence = float(metrics["confidence"])
    abstained = int(bool(metrics.get("abstained", False)))
    verify_ms = int(metrics.get("verify_ms", 0))
    with _hal_conn() as conn:
        conn.execute(
            "INSERT INTO hal_telemetry "
            "(event_id, run_id, model, task_type, support_ratio, citation_coverage, confidence, abstained, verify_ms, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (eid, run_id, model, task_type, support_ratio, citation_coverage, confidence, abstained, verify_ms, datetime.now(UTC).isoformat()),
        )
    return eid


def telemetry_summary_7d(*, alert_threshold: float = 0.70) -> dict[str, Any]:
    """HAL-26: 7-day verification metrics and threshold alert detector."""
    init_hallucination_db()
    cutoff = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    with _hal_conn() as conn:
        rows = conn.execute("SELECT * FROM hal_telemetry WHERE created_at >= ?", (cutoff,)).fetchall()
    if not rows:
        return {"count": 0, "avg_support_ratio": 1.0, "avg_confidence": 1.0, "abstention_rate": 0.0, "alert": False}
    avg_sup = sum(float(r["support_ratio"]) for r in rows) / len(rows)
    avg_conf = sum(float(r["confidence"]) for r in rows) / len(rows)
    abs_rate = sum(int(r["abstained"]) for r in rows) / len(rows)
    return {
        "count": len(rows),
        "avg_support_ratio": round(avg_sup, 4),
        "avg_confidence": round(avg_conf, 4),
        "abstention_rate": round(abs_rate, 4),
        "alert": avg_sup < alert_threshold,
    }


def submit_wrong_answer_report(
    *,
    run_id: str,
    prompt: str,
    bad_answer: str,
    corrected_answer: str,
    **meta: Any,
) -> dict[str, Any]:
    """HAL-25: User submits 'bu yanlış' report into admin review queue (approved=0 by default)."""
    init_hallucination_db()
    rid = f"rep-{uuid.uuid4().hex[:10]}"
    now = datetime.now(UTC).isoformat()
    source_url = str(meta.get("source_url", ""))
    taxonomy_class = str(meta.get("taxonomy_class", "fabricated_fact"))
    with _hal_conn() as conn:
        conn.execute(
            "INSERT INTO hal_reports "
            "(report_id, run_id, prompt, bad_answer, corrected_answer, source_url, taxonomy_class, approved, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)",
            (rid, run_id, prompt, bad_answer, corrected_answer, source_url, taxonomy_class, now),
        )
    return {"report_id": rid, "approved": False, "created_at": now}


def approve_wrong_answer_report(report_id: str) -> dict[str, Any] | None:
    init_hallucination_db()
    with _hal_conn() as conn:
        conn.execute("UPDATE hal_reports SET approved = 1 WHERE report_id = ?", (report_id,))
        row = conn.execute("SELECT * FROM hal_reports WHERE report_id = ?", (report_id,)).fetchone()
    return dict(row) if row else None


def list_approved_corrections() -> list[dict[str, Any]]:
    init_hallucination_db()
    with _hal_conn() as conn:
        rows = conn.execute("SELECT * FROM hal_reports WHERE approved = 1 ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def update_model_hallucination_profile(model: str, task_type: str, hallucination_rate: float, sample_count: int) -> None:
    """HAL-28: Persist per-model x task_type hallucination rates and feed penalty to gateway registry."""
    init_hallucination_db()
    now = datetime.now(UTC).isoformat()
    with _hal_conn() as conn:
        conn.execute(
            "INSERT INTO model_hallucination_profiles (model, task_type, hallucination_rate, sample_count, updated_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(model, task_type) DO UPDATE SET "
            "hallucination_rate = excluded.hallucination_rate, "
            "sample_count = excluded.sample_count, "
            "updated_at = excluded.updated_at",
            (model, task_type, float(hallucination_rate), int(sample_count), now),
        )


def get_model_hallucination_profiles() -> list[dict[str, Any]]:
    init_hallucination_db()
    with _hal_conn() as conn:
        rows = conn.execute("SELECT * FROM model_hallucination_profiles ORDER BY hallucination_rate ASC").fetchall()
    return [dict(r) for r in rows]
