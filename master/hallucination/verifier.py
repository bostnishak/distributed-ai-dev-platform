"""HAL-01, HAL-06..HAL-26, HAL-28: Claim Verification, NLI Entailment, Numeric/Code/Premise/High-Risk Guardrails & Telemetry."""

from __future__ import annotations

import ast
import importlib.util
import inspect
import logging
import re
import sqlite3
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import config
from rag.store import normalize_turkish_text, tr_lower

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
_DOSAGE_DIAG_RE = re.compile(
    r"\b(\d+\s*(?:mg|ml|tablet|doz)\s*(?:alın|kullanın|için)|kesin\s+teşhisiniz|bu\s+hisseyi\s+hemen\s+alın|yatırım\s+tavsiyesi\s+olarak\s+alın)\b",
    re.IGNORECASE,
)


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

    # Contradiction signals: high topical overlap with any conflicting/altered number or opposite polarity
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
        # Check for fabricated citation tags like [S9]
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
        elif v.status == "contradicted":
            removed.append(v.claim.text)
        elif strict:
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


# ---------------------------------------------------------------- HAL-09 Numeric & Table Sum Verification

def verify_numbers_and_tables(
    text: str,
    sources: list[dict[str, Any]] | None = None,
    tool_outputs: list[Any] | None = None,
) -> dict[str, Any]:
    """HAL-09: Verify numbers appear in sources/tools and check markdown table total-row arithmetic."""
    allowed_nums: set[str] = set()
    for src in sources or []:
        allowed_nums.update(_NUM_RE.findall(str(src.get("content") or src.get("quote") or "")))
    for out in tool_outputs or []:
        allowed_nums.update(_NUM_RE.findall(str(out)))

    found = _NUM_RE.findall(_FENCE_RE.sub(" ", text or ""))
    unsourced = [n for n in found if allowed_nums and n not in allowed_nums]

    # Check markdown table "Toplam/Total" row arithmetic
    table_errors: list[str] = []
    lines = (text or "").splitlines()
    for idx, ln in enumerate(lines):
        if "|" in ln and any(k in tr_lower(ln) for k in ("toplam", "total")):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            # Collect numeric rows directly above this total row
            above_rows: list[list[str]] = []
            j = idx - 1
            while j >= 0 and "|" in lines[j] and not re.match(r"^\s*\|?[\s:\-|]+\|$", lines[j]):
                above_rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j -= 1
            for col in range(1, len(cells)):
                try:
                    stated = float(cells[col].replace(",", ".").replace("%", "").strip())
                    col_vals = []
                    for r in above_rows:
                        if col < len(r):
                            col_vals.append(float(r[col].replace(",", ".").replace("%", "").strip()))
                    if col_vals and abs(sum(col_vals) - stated) > 1e-2:
                        table_errors.append(f"Sütun {col + 1} toplam uyuşmazlığı: beyan={stated}, hesap={round(sum(col_vals), 4)}")
                except ValueError:
                    continue

    return {
        "passed": len(unsourced) == 0 and len(table_errors) == 0,
        "unsourced_numbers": unsourced,
        "table_sum_errors": table_errors,
    }


# ---------------------------------------------------------------- HAL-10 Chain-of-Verification & HAL-11 Self-Consistency

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


# ---------------------------------------------------------------- HAL-12 & HAL-13 Code & API Existence Audit

def audit_python_code_apis(code: str) -> dict[str, Any]:
    """HAL-13: AST import & attribute checker catching hallucinated packages and nonexistent module APIs."""
    try:
        tree = ast.parse(code or "")
    except SyntaxError as exc:
        return {"syntax_ok": False, "passed": False, "errors": [f"Sözdizimi hatası (satır {exc.lineno}): {exc.msg}"]}

    missing_packages: list[str] = []
    missing_attrs: list[str] = []
    imported_modules: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if importlib.util.find_spec(top) is None:
                    missing_packages.append(alias.name)
                else:
                    imported_modules[alias.asname or top] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if importlib.util.find_spec(top) is None:
                missing_packages.append(node.module)
            else:
                try:
                    mod = __import__(node.module, fromlist=["*"])
                    for alias in node.names:
                        if alias.name != "*" and not hasattr(mod, alias.name):
                            missing_attrs.append(f"{node.module}.{alias.name}")
                except Exception as exc:
                    logging.getLogger(__name__).debug("AST import audit skipped for %s: %s", node.module, exc)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            mod_name = imported_modules.get(node.func.value.id)
            if mod_name:
                try:
                    mod = __import__(mod_name, fromlist=["*"])
                    if not hasattr(mod, node.func.attr):
                        missing_attrs.append(f"{mod_name}.{node.func.attr}")
                    else:
                        fn = getattr(mod, node.func.attr)
                        if callable(fn):
                            try:
                                sig = inspect.signature(fn)
                                kw_names = [kw.arg for kw in node.keywords if kw.arg]
                                has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
                                if not has_var_kw:
                                    for kw in kw_names:
                                        if kw not in sig.parameters:
                                            missing_attrs.append(f"{mod_name}.{node.func.attr}(bilinmeyen parametre: {kw})")
                            except (TypeError, ValueError) as exc:
                                logging.getLogger(__name__).debug("signature inspect skipped: %s", exc)
                except Exception as exc:
                    logging.getLogger(__name__).debug("AST attr audit skipped for %s: %s", mod_name, exc)

    return {
        "syntax_ok": True,
        "passed": len(missing_packages) == 0 and len(missing_attrs) == 0,
        "missing_packages": sorted(set(missing_packages)),
        "missing_apis": sorted(set(missing_attrs)),
    }


# ---------------------------------------------------------------- HAL-14 Confidence & HAL-15 Abstention

def compute_confidence(
    *,
    support_ratio: float = 0.0,
    rag_score: float = 0.0,
    consistency: float = 1.0,
    tool_verified: bool = False,
    has_sources: bool = False,
    calibrator=None,
) -> dict[str, Any]:
    """HAL-14: Combine grounding, consistency, and tool signals into a calibrated confidence score."""
    raw = (
        0.45 * max(0.0, min(1.0, support_ratio))
        + 0.20 * max(0.0, min(1.0, rag_score))
        + 0.20 * max(0.0, min(1.0, consistency))
        + (0.15 if tool_verified else 0.0)
    )
    if not has_sources and not tool_verified:
        raw = min(raw, 0.45)
    score = float(calibrator.calibrate(raw)) if calibrator is not None else round(min(0.99, max(0.01, raw)), 4)
    label = "yüksek" if score >= 0.78 else ("orta" if score >= 0.48 else "düşük")
    return {"score": round(score, 4), "label": label}


def decide_abstention(*, confidence_score: float, has_sources: bool, risk: str, is_factual: bool = True) -> dict[str, Any]:
    """HAL-15: Explicit abstention decision when evidence is missing on factual/high-risk requests."""
    should_abstain = (not has_sources and risk == "high") or (not has_sources and is_factual and confidence_score < 0.42)
    if should_abstain:
        return {
            "abstain": True,
            "message": (
                "Bu konuda güvenilir kaynak bulamadım ve bilgiyi doğrulayamadım. "
                "İlgili belgeyi bilgi bankasına yükleyebilir veya web aramasını etkinleştirebilirsin."
            ),
        }
    return {"abstain": False, "message": ""}


_FUTURE_MARKERS = (
    "yarın", "gelecek hafta", "gelecek yıl", "gelecek ay", "haftaya", "önümüzdeki", "bir sonraki", "sonraki",
    "tomorrow", "next week", "next year", "next month",
)
_PRIVATE_MARKERS = (
    "gizli", "özel telefon", "kişisel cep", "cep telefonu", "ev adresi", "şifresi", "parolası", "kimlik numarasını",
    "kredi kart", "tıbbi kayıt", "özel e-posta", "private", "confidential", "home address", "password of", "phone number of",
)
_FORECAST_VERBS = (
    "ne olacak", "kaç olacak", "olacak", "kapanış fiyatı", "closing price", "will close", "will it", "will be", "will win",
    "winning numbers", "kesin olarak", "tam tarih", "exact", "tam olarak", "şampiyon",
)
_REQUEST_VERBS = ("nedir", "söyle", "verir misin", "listele", "getir", "paylaş", "tell me", "what is", "give me", "who will")
# Questions about *how something works* are ordinary knowledge questions even when they mention a private-sounding word.
_EXPLAINER_MARKERS = ("nasıl", "how ", "how?", "farkı", "neden", "why ", "algoritma", "regex", "kriptografi", "nedir ve", "ne demek", "ne demektir")


def detect_unanswerable(question: str, *, current_year: int | None = None) -> dict[str, Any]:
    """HAL-15: questions nobody can answer truthfully (private data, exact future values) get an abstention up front.

    Conservative on purpose: it fires only on explicit private-data wording asked as a request for a value, or a
    *specific future value* (a future marker together with a forecast phrase, or a year after ``current_year``).
    Explanatory questions ("nasıl çalışır", "farkı nedir") are never refused.
    """
    year = current_year or datetime.now(UTC).year
    low = tr_lower(question)
    if any(m in low for m in _EXPLAINER_MARKERS) and not any(m in low for m in ("olacak", "will be", "tam olarak")):
        return {"unanswerable": False, "reason": "", "message": ""}
    asks_for_value = any(v in low for v in _REQUEST_VERBS) or "?" in low
    private = any(m in low for m in _PRIVATE_MARKERS) and asks_for_value
    future = any(m in low for m in _FUTURE_MARKERS) and any(v in low for v in _FORECAST_VERBS)
    future_year = any(int(y) > year + 1 for y in _DATE_RE.findall(low)) and any(v in low for v in ("tam olarak", "kaç", "exact", "olacak"))
    if private or future or future_year:
        reason = "private_data" if private else "future_value"
        return {
            "unanswerable": True,
            "reason": reason,
            "message": "Bu konuda güvenilir kaynak bulamadım ve bilgiyi doğrulayamadım; "
            + ("gizli/özel bir bilgi olduğu için paylaşamam." if private else "gelecekteki bir değeri tahmin edemem."),
        }
    return {"unanswerable": False, "reason": "", "message": ""}


# ---------------------------------------------------------------- HAL-16 False Premise, HAL-17 Entity/Standard, HAL-18 Clock

_KNOWN_TIMELINE_FACTS: tuple[tuple[str, int, int, str], ...] = (
    ("atatürk", 1881, 1938, "Mustafa Kemal Atatürk 1881-1938 yılları arasında yaşamıştır"),
    ("einstein", 1879, 1955, "Albert Einstein 1879-1955 yılları arasında yaşamıştır"),
    ("python", 1991, 2100, "Python programlama dili ilk kez 1991 yılında yayımlanmıştır"),
    ("türkiye cumhuriyeti", 1923, 2100, "Türkiye Cumhuriyeti 29 Ekim 1923 tarihinde kurulmuştur"),
)


def detect_false_premise(question: str) -> dict[str, Any]:
    """HAL-16: Detect chronological or factual false premises in user questions before answering."""
    low = tr_lower(question)
    years = [int(y) for y in _DATE_RE.findall(low)]
    if not years:
        return {"false_premise": False, "correction": ""}
    for entity, start_yr, end_yr, fact in _KNOWN_TIMELINE_FACTS:
        if entity in low:
            for yr in years:
                if yr < start_yr or yr > end_yr:
                    return {
                        "false_premise": True,
                        "entity": entity,
                        "invalid_year": yr,
                        "correction": f"Öncül düzeltmesi: {fact}; bu nedenle {yr} yılına ait bu öncül doğru değildir.",
                    }
    return {"false_premise": False, "correction": ""}


def verify_standard_and_law_numbers(text: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    """HAL-17: Catch unsourced ISO/DIN/TS standard numbers and law article citations."""
    mentioned = _STD_LAW_RE.findall(text or "")
    src_blob = " ".join(str(s.get("content") or s.get("quote") or "") for s in sources)
    unverified = [m for m in mentioned if tr_lower(m) not in tr_lower(src_blob)]
    return {"mentioned": mentioned, "unverified": unverified, "passed": len(unverified) == 0}


def datetime_tool(days_offset: int = 0) -> dict[str, Any]:
    """HAL-18: Deterministic system clock and date arithmetic."""
    now = datetime.now(UTC)
    target = now + timedelta(days=int(days_offset))
    return {"utc_now": now.isoformat(), "target_date": target.strftime("%Y-%m-%d"), "days_offset": int(days_offset)}


# ---------------------------------------------------------------- HAL-19 High-Risk, HAL-21 Chat Consistency, HAL-23 Slides, HAL-24 Memory Poisoning

def apply_high_risk_guardrails(text: str, *, domain: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    """HAL-19: Mandatory sources, disclaimer, and zero diagnosis/dosage/investment prescriptions."""
    if not sources:
        return {
            "blocked": True,
            "text": "Yüksek riskli alanda (sağlık/hukuk/finans) doğrulanmış kaynak olmadan yanıt verilemez.",
            "reason": "no_sources_high_risk",
        }
    if _DOSAGE_DIAG_RE.search(text or ""):
        return {
            "blocked": True,
            "text": "Tıbbi teşhis/dozaj veya doğrudan yatırım tavsiyesi üretilemez. Lütfen yetkili bir uzmana danışın.",
            "reason": "forbidden_prescription",
        }
    disclaimer = "Not: Bu bilgiler yalnızca genel bilgilendirme amaçlıdır; profesyonel tıbbi, hukuki veya finansal tavsiye yerine geçmez."
    out = text if disclaimer.lower() in (text or "").lower() else f"{text.strip()}\n\n{disclaimer}"
    return {"blocked": False, "text": out, "reason": "ok"}


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


def verify_presentation_sources(slides: list[dict[str, Any]], sources: list[dict[str, Any]]) -> dict[str, Any]:
    """HAL-23: Verify every factual slide bullet links to a real source and append a verified Kaynaklar slide."""
    valid_ids = {str(s.get("id") or f"S{i + 1}") for i, s in enumerate(sources)}
    verified_bullets = 0
    total_bullets = 0
    for sl in slides:
        for b in sl.get("bullets") or []:
            total_bullets += 1
            if any(f"[{sid}]" in str(b) for sid in valid_ids):
                verified_bullets += 1
    sources_slide = {
        "title": "Kaynaklar",
        "bullets": [f"[{s.get('id', f'S{i + 1}')}] {s.get('doc') or s.get('title') or s.get('url', '')}" for i, s in enumerate(sources)],
    }
    ratio = round(verified_bullets / max(1, total_bullets), 4)
    return {"coverage_ratio": ratio, "sources_slide": sources_slide, "passed": ratio >= 0.95 or total_bullets == 0}


def guard_memory_write(fact: str, *, source_origin: str) -> dict[str, Any]:
    """HAL-24: Prevent memory poisoning by rejecting facts extracted from documents or web pages."""
    if source_origin != "user_turn":
        return {"allowed": False, "reason": f"Hafıza zehirlenmesi koruması: '{source_origin}' kaynağından hafıza yazılamaz."}
    if len((fact or "").strip()) < 4:
        return {"allowed": False, "reason": "Boş veya geçersiz hafıza kaydı."}
    return {"allowed": True, "reason": "ok"}


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
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS hal_telemetry (
                event_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                model TEXT NOT NULL,
                task_type TEXT NOT NULL,
                support_ratio REAL NOT NULL,
                citation_coverage REAL NOT NULL,
                confidence REAL NOT NULL,
                abstained INTEGER NOT NULL DEFAULT 0,
                verify_ms INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS hal_reports (
                report_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                prompt TEXT NOT NULL,
                bad_answer TEXT NOT NULL,
                corrected_answer TEXT NOT NULL,
                source_url TEXT NOT NULL DEFAULT '',
                taxonomy_class TEXT NOT NULL DEFAULT 'fabricated_fact',
                approved INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS model_hallucination_profiles (
                model TEXT NOT NULL,
                task_type TEXT NOT NULL,
                hallucination_rate REAL NOT NULL,
                sample_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (model, task_type)
            );
            """
        )


def log_verification_telemetry(
    *,
    run_id: str,
    model: str,
    task_type: str,
    support_ratio: float,
    citation_coverage: float,
    confidence: float,
    abstained: bool = False,
    verify_ms: int = 0,
) -> str:
    init_hallucination_db()
    eid = f"ht-{uuid.uuid4().hex[:10]}"
    with _hal_conn() as conn:
        conn.execute(
            """
            INSERT INTO hal_telemetry
                (event_id, run_id, model, task_type, support_ratio, citation_coverage, confidence, abstained, verify_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (eid, run_id, model, task_type, float(support_ratio), float(citation_coverage), float(confidence), int(abstained), int(verify_ms), datetime.now(UTC).isoformat()),
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
    source_url: str = "",
    taxonomy_class: str = "fabricated_fact",
) -> dict[str, Any]:
    """HAL-25: User submits 'bu yanlış' report into admin review queue (approved=0 by default)."""
    init_hallucination_db()
    rid = f"rep-{uuid.uuid4().hex[:10]}"
    now = datetime.now(UTC).isoformat()
    with _hal_conn() as conn:
        conn.execute(
            """
            INSERT INTO hal_reports
                (report_id, run_id, prompt, bad_answer, corrected_answer, source_url, taxonomy_class, approved, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
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
            """
            INSERT INTO model_hallucination_profiles (model, task_type, hallucination_rate, sample_count, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(model, task_type) DO UPDATE SET
                hallucination_rate = excluded.hallucination_rate,
                sample_count = excluded.sample_count,
                updated_at = excluded.updated_at
            """,
            (model, task_type, float(hallucination_rate), int(sample_count), now),
        )


def get_model_hallucination_profiles() -> list[dict[str, Any]]:
    init_hallucination_db()
    with _hal_conn() as conn:
        rows = conn.execute("SELECT * FROM model_hallucination_profiles ORDER BY hallucination_rate ASC").fetchall()
    return [dict(r) for r in rows]
