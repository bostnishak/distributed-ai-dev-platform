"""HAL-09, HAL-12..HAL-19, HAL-23, HAL-24: Numeric/Table Audit, Code API Audit, Confidence, Guardrails & Premise Checks."""

from __future__ import annotations

import ast
import importlib.util
import inspect
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from rag.store import tr_lower

_FENCE_RE = re.compile(r"```[\s\S]*?```")
_NUM_RE = re.compile(r"\b\d+(?:[.,]\d+)?%?\b")
_DATE_RE = re.compile(r"\b(?:1[0-9]{3}|20[0-9]{2})\b")
_STD_LAW_RE = re.compile(
    r"\b(?:ISO\s*\d{3,5}(?:-\d+)?|DIN\s*\d{3,5}|TS\s*\d{3,5}|TCK\s*m\.\s*\d+|TBK\s*m\.\s*\d+|KVKK\s*m\.\s*\d+|Madde\s*\d+)\b",
    re.IGNORECASE,
)
_DOSAGE_DIAG_RE = re.compile(
    r"\b(\d+\s*(?:mg|ml|tablet|doz)\s*(?:alın|kullanın|için)|kesin\s+teşhisiniz|bu\s+hisseyi\s+hemen\s+alın|yatırım\s+tavsiyesi\s+olarak\s+alın)\b",
    re.IGNORECASE,
)

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
_EXPLAINER_MARKERS = ("nasıl", "how ", "how?", "farkı", "neden", "why ", "algoritma", "regex", "kriptografi", "nedir ve", "ne demek", "ne demektir")

_KNOWN_TIMELINE_FACTS: tuple[tuple[str, int, int, str], ...] = (
    ("atatürk", 1881, 1938, "Mustafa Kemal Atatürk 1881-1938 yılları arasında yaşamıştır"),
    ("einstein", 1879, 1955, "Albert Einstein 1879-1955 yılları arasında yaşamıştır"),
    ("python", 1991, 2100, "Python programlama dili ilk kez 1991 yılında yayımlanmıştır"),
    ("türkiye cumhuriyeti", 1923, 2100, "Türkiye Cumhuriyeti 29 Ekim 1923 tarihinde kurulmuştur"),
)


# ---------------------------------------------------------------- HAL-09 Numeric & Table Sum Verification

def _collect_table_row_errors(lines: list[str], idx: int) -> list[str]:
    cells = [c.strip() for c in lines[idx].strip().strip("|").split("|")]
    above_rows: list[list[str]] = []
    j = idx - 1
    while j >= 0 and "|" in lines[j] and not re.match(r"^\s*\|?[\s:\-|]+\|$", lines[j]):
        above_rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
        j -= 1
    errors: list[str] = []
    for col in range(1, len(cells)):
        try:
            stated = float(cells[col].replace(",", ".").replace("%", "").strip())
            col_vals = [float(r[col].replace(",", ".").replace("%", "").strip()) for r in above_rows if col < len(r)]
            if col_vals and abs(sum(col_vals) - stated) > 1e-2:
                errors.append(f"Sütun {col + 1} toplam uyuşmazlığı: beyan={stated}, hesap={round(sum(col_vals), 4)}")
        except ValueError:
            continue
    return errors


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

    table_errors: list[str] = []
    lines = (text or "").splitlines()
    for idx, ln in enumerate(lines):
        if "|" in ln and any(k in tr_lower(ln) for k in ("toplam", "total")):
            table_errors.extend(_collect_table_row_errors(lines, idx))

    return {
        "passed": len(unsourced) == 0 and len(table_errors) == 0,
        "unsourced_numbers": unsourced,
        "table_sum_errors": table_errors,
    }


# ---------------------------------------------------------------- HAL-12 & HAL-13 Code & API Existence Audit

def _audit_import_from(node: ast.ImportFrom, missing_packages: list[str], missing_attrs: list[str]) -> None:
    if not node.module:
        return
    top = node.module.split(".")[0]
    if importlib.util.find_spec(top) is None:
        missing_packages.append(node.module)
        return
    try:
        mod = __import__(node.module, fromlist=["*"])
        for alias in node.names:
            if alias.name != "*" and not hasattr(mod, alias.name):
                missing_attrs.append(f"{node.module}.{alias.name}")
    except (ImportError, OSError, RuntimeError, ValueError, TypeError, AttributeError, SyntaxError) as exc:
        logging.getLogger(__name__).debug("AST import audit skipped for %s: %s", node.module, exc)


def _audit_call_keywords(fn: Any, node: ast.Call, mod_name: str, missing_attrs: list[str]) -> None:
    if not callable(fn):
        return
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError) as exc:
        logging.getLogger(__name__).debug("signature inspect skipped: %s", exc)
        return
    has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    if has_var_kw:
        return
    attr_name = node.func.attr if isinstance(node.func, ast.Attribute) else ""
    for kw in (k.arg for k in node.keywords if k.arg):
        if kw not in sig.parameters:
            missing_attrs.append(f"{mod_name}.{attr_name}(bilinmeyen parametre: {kw})")


def _audit_module_call(node: ast.Call, imported_modules: dict[str, str], missing_attrs: list[str]) -> None:
    if not (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)):
        return
    mod_name = imported_modules.get(node.func.value.id)
    if not mod_name:
        return
    try:
        mod = __import__(mod_name, fromlist=["*"])
        if not hasattr(mod, node.func.attr):
            missing_attrs.append(f"{mod_name}.{node.func.attr}")
            return
        _audit_call_keywords(getattr(mod, node.func.attr), node, mod_name, missing_attrs)
    except (ImportError, OSError, RuntimeError, ValueError, TypeError, AttributeError, SyntaxError) as exc:
        logging.getLogger(__name__).debug("AST attr audit skipped for %s: %s", mod_name, exc)


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
        elif isinstance(node, ast.ImportFrom):
            _audit_import_from(node, missing_packages, missing_attrs)
        elif isinstance(node, ast.Call):
            _audit_module_call(node, imported_modules, missing_attrs)

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
    **options: Any,
) -> dict[str, Any]:
    """HAL-14: Combine grounding, consistency, and tool signals into a calibrated confidence score.

    Accepts optional keyword flags: ``tool_verified: bool = False``, ``has_sources: bool = False``, ``calibrator=None``.
    """
    tool_verified = bool(options.get("tool_verified", False))
    has_sources = bool(options.get("has_sources", False))
    calibrator = options.get("calibrator")
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


def _has_word(text: str, marker: str) -> bool:
    """Whole-word match so that 'gizli' does not fire on 'gizliliği' and 'getir' not on 'getirir'."""
    return re.search(rf"(?<!\w){re.escape(marker)}(?!\w)", text) is not None


def detect_unanswerable(question: str, *, current_year: int | None = None) -> dict[str, Any]:
    """HAL-15: questions nobody can answer truthfully (private data, exact future values) get an abstention up front."""
    year = current_year or datetime.now(UTC).year
    low = tr_lower(question)
    if any(m in low for m in _EXPLAINER_MARKERS) and not any(m in low for m in ("olacak", "will be", "tam olarak")):
        return {"unanswerable": False, "reason": "", "message": ""}
    if len(low) > 400:  # a pasted text to work on, not a question about a secret value
        return {"unanswerable": False, "reason": "", "message": ""}
    asks_for_value = any(_has_word(low, v) for v in _REQUEST_VERBS) or "?" in low
    private = any(_has_word(low, m) for m in _PRIVATE_MARKERS) and asks_for_value
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
    target = now + timedelta(days=days_offset)
    return {"utc_now": now.isoformat(), "target_date": target.strftime("%Y-%m-%d"), "days_offset": days_offset}


# ---------------------------------------------------------------- HAL-19 High-Risk, HAL-23 Slides, HAL-24 Memory Poisoning

def apply_high_risk_guardrails(text: str, *, domain: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    """HAL-19: Mandatory sources, disclaimer, and zero diagnosis/dosage/investment prescriptions."""
    norm_domain = (domain or "high_risk").strip().lower()
    if not sources:
        return {
            "blocked": True,
            "domain": norm_domain,
            "text": "Yüksek riskli alanda (sağlık/hukuk/finans) doğrulanmış kaynak olmadan yanıt verilemez.",
            "reason": "no_sources_high_risk",
        }
    if _DOSAGE_DIAG_RE.search(text or ""):
        return {
            "blocked": True,
            "domain": norm_domain,
            "text": "Tıbbi teşhis/dozaj veya doğrudan yatırım tavsiyesi üretilemez. Lütfen yetkili bir uzmana danışın.",
            "reason": "forbidden_prescription",
        }
    disclaimer = "Not: Bu bilgiler yalnızca genel bilgilendirme amaçlıdır; profesyonel tıbbi, hukuki veya finansal tavsiye yerine geçmez."
    out = text if disclaimer.lower() in (text or "").lower() else f"{text.strip()}\n\n{disclaimer}"
    return {"blocked": False, "domain": norm_domain, "text": out, "reason": "ok"}


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
