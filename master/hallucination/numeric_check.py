"""EPK-07: Sentence-Level Citation Mapper & Numeric/Unit Consistency Verifier."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/hallucination", tags=["hallucination-numeric"])

_NUM_UNIT_RE = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*(km|m|cm|mm|kg|g|gb|mb|ms|s|sn|tl|usd|eur|%|°c|c)?\b",
    re.IGNORECASE,
)
_UNIT_NORM: dict[str, tuple[str, float]] = {
    "km": ("length_m", 1000.0), "m": ("length_m", 1.0), "cm": ("length_m", 0.01), "mm": ("length_m", 0.001),
    "kg": ("mass_g", 1000.0), "g": ("mass_g", 1.0),
    "gb": ("data_mb", 1024.0), "mb": ("data_mb", 1.0),
    "s": ("time_ms", 1000.0), "sn": ("time_ms", 1000.0), "ms": ("time_ms", 1.0),
    "%": ("percent", 1.0), "tl": ("try", 1.0), "usd": ("usd", 1.0), "eur": ("eur", 1.0),
    "°c": ("temp_c", 1.0), "c": ("temp_c", 1.0),
}
_CIT_RE = re.compile(r"\[(S\d+)\]")


def extract_normalized_quantities(text: str) -> list[dict[str, Any]]:
    """Extract numbers and normalize compatible physical/financial units into canonical dimensions."""
    out: list[dict[str, Any]] = []
    for m in _NUM_UNIT_RE.finditer(text or ""):
        raw_num = m.group(1).replace(",", ".")
        try:
            val = float(raw_num)
        except ValueError:
            continue
        unit = (m.group(2) or "").lower()
        dim, mult = _UNIT_NORM.get(unit, ("scalar", 1.0))
        out.append({"raw": m.group(0).strip(), "value": val, "unit": unit, "dim": dim, "canonical": val * mult})
    return out


def _quantity_supported(q: dict[str, Any], source_quants: list[dict[str, Any]], rel_tol: float = 0.015) -> bool:
    for sq in source_quants:
        if q["dim"] != sq["dim"] and "scalar" not in (q["dim"], sq["dim"]):
            continue
        base = max(abs(sq["canonical"]), 1e-9)
        if abs(q["canonical"] - sq["canonical"]) / base <= rel_tol or abs(q["value"] - sq["value"]) <= 1e-6:
            return True
    return False


def _sentence_overlap(sentence: str, src_text: str) -> float:
    s_toks = {t for t in re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+", sentence.lower()) if len(t) >= 3}
    t_toks = {t for t in re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+", src_text.lower()) if len(t) >= 3}
    return len(s_toks & t_toks) / max(1, len(s_toks))


def verify_numeric_and_citations(answer: str, sources: list[dict[str, str]]) -> dict[str, Any]:
    """Verify sentence-level citation mapping and numeric/unit consistency against source passages."""
    src_map = {str(s.get("id") or f"S{i + 1}"): str(s.get("text") or s.get("content") or "") for i, s in enumerate(sources)}
    all_source_quants = [q for txt in src_map.values() for q in extract_normalized_quantities(txt)]

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", (answer or "").strip()) if s.strip()]
    checked: list[dict[str, Any]] = []
    total_nums = 0
    supported_nums = 0
    cited_sentences = 0

    for sent in sentences:
        explicit_cits = _CIT_RE.findall(sent)
        best_src = max(src_map.items(), key=lambda kv: _sentence_overlap(sent, kv[1]), default=("", ""))
        matched_src_id = best_src[0] if best_src[0] and _sentence_overlap(sent, best_src[1]) >= 0.2 else None
        if explicit_cits or matched_src_id:
            cited_sentences += 1

        quants = extract_normalized_quantities(sent)
        mismatches: list[str] = []
        for q in quants:
            total_nums += 1
            if _quantity_supported(q, all_source_quants):
                supported_nums += 1
            else:
                mismatches.append(q["raw"])
        checked.append({
            "sentence": sent,
            "explicit_citations": explicit_cits,
            "suggested_source": matched_src_id,
            "quantities": [q["raw"] for q in quants],
            "unsupported_numbers": mismatches,
            "numeric_ok": len(mismatches) == 0,
        })

    num_score = round(supported_nums / total_nums, 3) if total_nums else 1.0
    cit_cov = round(cited_sentences / max(1, len(sentences)), 3) if sentences else 1.0
    return {
        "ok": True,
        "passed": num_score >= 0.9 and cit_cov >= 0.5,
        "numeric_consistency": num_score,
        "citation_coverage": cit_cov,
        "total_numbers": total_nums,
        "supported_numbers": supported_nums,
        "sentences": checked,
    }


class NumericVerifyRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=16000)
    sources: list[dict[str, str]] = Field(default_factory=list)


@router.post("/numeric-verify")
async def api_numeric_verify(body: NumericVerifyRequest):
    """Run sentence-level citation mapping and numeric/unit consistency verification."""
    return verify_numeric_and_citations(body.answer, body.sources)
