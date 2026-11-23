"""MODE-01..MODE-08: Programmatic Output Contracts, Mode Enforcement & Format Directives."""

from __future__ import annotations

import ast
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

_FENCE_RE = re.compile(r"```([a-zA-Z0-9_+-]*)\n(.*?)```", re.DOTALL)
_CITATION_RE = re.compile(r"(\[\d+\]|\[Kaynak:[^\]]+\]|https?://\S+)")
_PREAMBLE_RE = re.compile(
    r"^\s*(?:tabii(?:\s+ki)?|harika\s+soru|memnuniyetle|elbette|sure|certainly|great\s+question|of\s+course)[!:,.\s-]*",
    re.IGNORECASE,
)
_FAST_PRESENTATION_RE = re.compile(
    r"\b(hemen\s+oluştur|direkt\s+üret|taslaksız|generate\s+now|immediately|skip\s+outline)\b",
    re.IGNORECASE,
)

# 6 mandatory sections for lesson mode (MODE-03)
LESSON_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Kısa Tanım", ("kısa tanım", "tanım", "nedir", "definition", "overview")),
    ("Sezgisel Benzetme", ("benzetme", "analoji", "analogy", "intuition", "sezgisel")),
    ("Adım Adım Açıklama", ("adım adım", "nasıl çalışır", "step by step", "açıklama", "explanation")),
    ("Çalışan Örnek", ("örnek", "example", "uygulama", "```")),
    ("Sık Yapılan Hatalar", ("sık yapılan", "hata", "tuzak", "common mistake", "pitfall")),
    ("Mini Alıştırma", ("alıştırma", "soru", "exercise", "pratik", "kendini dene")),
)


@dataclass
class ResponseContract:
    mode: str
    allowed_blocks: tuple[str, ...] = ("text", "code", "table", "list")
    required_sections: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ("emoji",)
    max_words: int | None = None
    max_sentences: int | None = None
    language: str = "tr"
    citation_policy: str = "optional"  # optional | required
    format_directives: tuple[str, ...] = ()
    outline_first: bool = False


@dataclass
class ContractValidation:
    passed: bool
    mode: str
    violations: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


def _tr_lower(text: str) -> str:
    return (text or "").replace("İ", "i").replace("I", "ı").lower()


def parse_format_directives(user_text: str) -> list[str]:
    """MODE-08: Extract explicit user formatting instructions from prompt."""
    low = _tr_lower(user_text)
    directives: list[str] = []
    if any(k in low for k in ("madde madde", "maddeler halinde", "bullet", "liste halinde")):
        directives.append("bullet_list")
    if any(k in low for k in ("tablo", "table", "karşılaştırma tablosu")):
        directives.append("table")
    if any(k in low for k in ("kısa tut", "kısaca", "tek cümle", "briefly", "short answer", "uzatmadan")):
        directives.append("short")
    if any(k in low for k in ("sadece kod", "yalnızca kod", "code only", "only code", "açıklamasız kod")):
        directives.append("code_only")
    if any(k in low for k in ("ingilizce", "in english", "english only")):
        directives.append("lang_en")
    if any(k in low for k in ("türkçe", "in turkish")):
        directives.append("lang_tr")
    if any(k in low for k in ("json format", "sadece json", "valid json")):
        directives.append("json_only")
    return directives


def build_contract(
    mode: str,
    *,
    user_text: str = "",
    language: str = "tr",
    outline_approved: bool = False,
) -> ResponseContract:
    """MODE-01: Build explicit programmatic ResponseContract for the active mode + user directives."""
    directives = parse_format_directives(user_text)
    effective_mode = mode
    if "code_only" in directives:
        effective_mode = "code_only"
    elif "short" in directives and effective_mode == "general":
        effective_mode = "short"

    effective_lang = "en" if "lang_en" in directives else ("tr" if "lang_tr" in directives else language)

    if effective_mode == "code_only":
        return ResponseContract(
            mode="code_only",
            allowed_blocks=("code",),
            forbidden=("prose_outside_code", "preamble", "emoji"),
            language=effective_lang,
            format_directives=tuple(directives),
        )
    if effective_mode == "lesson":
        return ResponseContract(
            mode="lesson",
            required_sections=tuple(name for name, _ in LESSON_SECTIONS),
            language=effective_lang,
            format_directives=tuple(directives),
        )
    if effective_mode == "research":
        return ResponseContract(
            mode="research",
            citation_policy="required",
            language=effective_lang,
            format_directives=tuple(directives),
        )
    if effective_mode == "presentation":
        fast_gen = bool(_FAST_PRESENTATION_RE.search(user_text or "")) or outline_approved
        return ResponseContract(
            mode="presentation",
            outline_first=not fast_gen,
            language=effective_lang,
            format_directives=tuple(directives),
        )
    if effective_mode == "project":
        return ResponseContract(
            mode="project",
            max_words=120,
            forbidden=("raw_code_dump", "emoji"),
            language=effective_lang,
            format_directives=tuple(directives),
        )
    if effective_mode == "short":
        return ResponseContract(
            mode="short",
            max_words=45,
            max_sentences=3,
            forbidden=("preamble", "emoji"),
            language=effective_lang,
            format_directives=tuple(directives),
        )
    return ResponseContract(
        mode="general",
        language=effective_lang,
        format_directives=tuple(directives),
    )


def _strip_code_fences(text: str) -> str:
    return _FENCE_RE.sub("", text or "").strip()


def _count_sentences(text: str) -> int:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return 0
    parts = [p for p in re.split(r"[.!?]+(?:\s+|$)", clean) if p.strip()]
    return max(1, len(parts))


def validate_contract(text: str, contract: ResponseContract) -> ContractValidation:
    """Programmatically verify an LLM response against its ResponseContract."""
    body = (text or "").strip()
    violations: list[str] = []
    metrics: dict[str, Any] = {}

    if not body:
        return ContractValidation(passed=False, mode=contract.mode, violations=["empty_response"])

    # MODE-02: code_only
    if contract.mode == "code_only":
        blocks = _FENCE_RE.findall(body)
        outside = _strip_code_fences(body)
        metrics["code_blocks"] = len(blocks)
        metrics["outside_chars"] = len(outside)
        if not blocks:
            violations.append("code_only_missing_code_block")
        if outside:
            violations.append("code_only_prose_outside_fences")
        for lang, code in blocks:
            if lang.lower() in ("py", "python"):
                try:
                    ast.parse(code)
                except SyntaxError as exc:
                    violations.append(f"python_syntax_error:{exc.msg}")

    # MODE-03: lesson (6 sections)
    if contract.mode == "lesson":
        low = body.lower()
        missing = []
        for sec_name, needles in LESSON_SECTIONS:
            if not any(n in low for n in needles):
                missing.append(sec_name)
        metrics["missing_sections"] = missing
        if missing:
            violations.append(f"lesson_missing_sections:{','.join(missing)}")

    # MODE-04: research (citations required)
    if contract.citation_policy == "required":
        cites = _CITATION_RE.findall(body)
        metrics["citation_count"] = len(cites)
        if not cites:
            violations.append("research_missing_citations")

    # MODE-05: presentation outline_first
    if contract.mode == "presentation" and contract.outline_first:
        low = body.lower()
        if not any(k in low for k in ("slayt", "slide", "taslak", "outline")):
            violations.append("presentation_missing_outline")

    # MODE-06: project summary <= 120 words, no raw file dump
    if contract.mode == "project":
        words = body.split()
        metrics["word_count"] = len(words)
        if len(words) > (contract.max_words or 120):
            violations.append(f"project_summary_too_long:{len(words)}")
        if len(_FENCE_RE.findall(body)) > 0 and len(body) > 600:
            violations.append("project_contains_raw_code_dump")

    # MODE-07: short (<= 3 sentences, <= 45 words, no preamble)
    if contract.mode == "short":
        words = body.split()
        sents = _count_sentences(body)
        metrics["word_count"] = len(words)
        metrics["sentence_count"] = sents
        if contract.max_words and len(words) > contract.max_words:
            violations.append(f"short_word_limit_exceeded:{len(words)}")
        if contract.max_sentences and sents > contract.max_sentences:
            violations.append(f"short_sentence_limit_exceeded:{sents}")
        if _PREAMBLE_RE.match(body):
            violations.append("short_contains_preamble")

    # MODE-08: explicit format directives
    if "bullet_list" in contract.format_directives:
        if not re.search(r"(?m)^\s*(?:[-*]|\d+\.)\s+", body):
            violations.append("directive_missing_bullet_list")
    if "table" in contract.format_directives:
        if "|" not in body or "---" not in body:
            violations.append("directive_missing_markdown_table")

    return ContractValidation(
        passed=len(violations) == 0,
        mode=contract.mode,
        violations=violations,
        metrics=metrics,
    )


def deterministic_repair(text: str, contract: ResponseContract, validation: ContractValidation) -> str:
    """Fast deterministic repair pass for structural mode violations before escalating to LLM repair."""
    body = (text or "").strip()

    if contract.mode == "code_only":
        blocks = _FENCE_RE.findall(body)
        if blocks:
            return "\n\n".join(f"```{lang}\n{code.strip()}\n```" for lang, code in blocks)
        return f"```python\n{body}\n```"

    if contract.mode == "short":
        body = _PREAMBLE_RE.sub("", body).strip()
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
        if contract.max_sentences and len(sents) > contract.max_sentences:
            body = " ".join(sents[: contract.max_sentences])
        words = body.split()
        if contract.max_words and len(words) > contract.max_words:
            body = " ".join(words[: contract.max_words]).rstrip(",;:") + "."
        return body

    if contract.mode == "project" and contract.max_words:
        body = _FENCE_RE.sub("", body).strip()
        words = body.split()
        if len(words) > contract.max_words:
            body = " ".join(words[: contract.max_words]).rstrip(",;:") + "."
        return body

    if "bullet_list" in contract.format_directives and "directive_missing_bullet_list" in validation.violations:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
        if sents:
            return "\n".join(f"- {s}" for s in sents)

    return body


async def enforce_contract(
    text: str,
    contract: ResponseContract,
    *,
    llm_repair_fn: Callable[[str, list[str]], Awaitable[str]] | None = None,
) -> tuple[str, ContractValidation]:
    """MODE-01/MODE-08: Validate, apply deterministic or single LLM repair pass, re-validate."""
    val = validate_contract(text, contract)
    if val.passed:
        return text, val

    repaired = deterministic_repair(text, contract, val)
    val2 = validate_contract(repaired, contract)
    if val2.passed or llm_repair_fn is None:
        return repaired, val2

    # Single LLM repair loop when deterministic fix wasn't sufficient (e.g. missing lesson sections/citations)
    llm_fixed = await llm_repair_fn(repaired, val2.violations)
    val3 = validate_contract(llm_fixed, contract)
    return llm_fixed, val3
