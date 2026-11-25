"""Deterministic 0-100 quality score for a generated deck (slide count, fullness, variety, honesty about numbers, language, topic fit)."""

from __future__ import annotations

import itertools
import re
from typing import Any

import pptx_guard

_GENERIC_TITLES = {"giriş", "özet", "sonuç", "teşekkürler", "genel bakış", "introduction", "summary", "conclusion", "overview", "thank you"}
_COUNT_RE = re.compile(r"(\d{1,2})[\s-]*(?:adet\s*|tane\s*)?(?:slayt|sayfa|slides?)", re.IGNORECASE)
_TR_CHARS = "çğıöşüÇĞİÖŞÜ"
_EN_WORDS = re.compile(r"\b(?:the|and|for|with|presentation|slides?|deck|company|create|about)\b", re.IGNORECASE)


def _items(slide: dict[str, Any]) -> list[str]:
    cols = slide.get("columns") or {}
    table_rows = [" | ".join(map(str, r)) for r in (slide.get("table") or {}).get("rows", []) if isinstance(r, list)]
    return [str(b) for b in [*(slide.get("bullets") or []), *(cols.get("left_bullets") or []), *(cols.get("right_bullets") or []), *table_rows]]


def _all_text(slides: list[dict[str, Any]]) -> str:
    return " ".join(" ".join([str(s.get("title", "")), str(s.get("key_fact", "")), str(s.get("notes", "")), *_items(s)]) for s in slides)


def _count_issue(total: int, request: str) -> tuple[int, str] | None:
    m = _COUNT_RE.search(request)
    if m and total != int(m.group(1)):
        return (15 if abs(total - int(m.group(1))) > 1 else 6), f"{m.group(1)} slayt istenmiş, {total} üretilmiş"
    return None


def _fullness_issues(slides: list[dict[str, Any]]) -> list[tuple[int, str]]:
    out = []
    thin = [s for s in slides if len(_items(s)) < 3 and not s.get("chart") and not s.get("kpis")]
    if thin:
        out.append((min(24, 8 * len(thin)), f"{len(thin)} slaytta 3'ten az madde var; her slayt dolu olmalı"))
    no_notes = [s for s in slides if len(str(s.get("notes") or "")) < 30]
    if no_notes:
        out.append((min(10, 3 * len(no_notes)), f"{len(no_notes)} slaytta konuşmacı notu eksik/çok kısa"))
    no_fact = [s for s in slides if not str(s.get("key_fact") or "").strip() and s.get("layout") not in ("table",)]
    if len(no_fact) > len(slides) // 2:
        out.append((5, "çoğu slaytta tek cümlelik çıkarım (key_fact) yok"))
    return out


def _variety_issues(slides: list[dict[str, Any]]) -> list[tuple[int, str]]:
    layouts = [str(s.get("layout") or "bullets") for s in slides]
    out = []
    if len(slides) >= 5 and len(set(layouts)) < 3:
        out.append((12, "düzen çeşitliliği yetersiz: çoğu slayt aynı yerleşimde"))
    repeats = sum(1 for a, b in itertools.pairwise(layouts) if a == b and a != "closing")
    if repeats >= 2:
        out.append((6, "arka arkaya aynı yerleşim kullanılmış"))
    return out


def _title_issues(slides: list[dict[str, Any]]) -> list[tuple[int, str]]:
    titles = [str(s.get("title", "")).strip().lower() for s in slides]
    out = []
    if len(set(titles)) < len(titles):
        out.append((10, "aynı başlıklı slaytlar var"))
    if sum(1 for t in titles if t in _GENERIC_TITLES) > 1:
        out.append((8, "başlıklar çok genel; konuya özgü başlık yaz"))
    if any(len(t.split()) < 2 for t in titles):
        out.append((4, "tek kelimelik başlıklar var"))
    return out


def _honesty_issues(slides: list[dict[str, Any]], request: str) -> list[tuple[int, str]]:
    facts = pptx_guard._Facts(request)  # same supported-number rules as the guard
    bad = [t for s in slides for t in [str(s.get("key_fact", "")), *_items(s)] if facts.invented(t)]
    out = [(min(30, 10 * len(bad)), f"{len(bad)} yerde istekte olmayan istatistik/sayı var")] if bad else []
    text = _all_text(slides)
    if re.search(r"<[^>\n]{2,40}>|lorem|\[\.\.\.|\bTODO\b", text, re.IGNORECASE):
        out.append((15, "yer tutucu / şablon metin kalmış"))
    return out


def _topic_language_issues(slides: list[dict[str, Any]], request: str) -> list[tuple[int, str]]:
    text, out = _all_text(slides), []
    words = {w for w in re.findall(r"\w{5,}", request.lower()) if not w.isdigit()}
    if words and sum(1 for w in words if w[:5] in text.lower()) < max(1, len(words) // 4):
        out.append((15, "içerik istenen konudan uzak görünüyor"))
    tr_ratio = sum(1 for ch in text if ch in _TR_CHARS) / max(1, len(text))
    wants_en = bool(_EN_WORDS.search(request)) and not any(ch in request for ch in _TR_CHARS)
    if wants_en and tr_ratio > 0.01:
        out.append((12, "İngilizce istenmiş ama metin Türkçe"))
    if not wants_en and any(ch in request for ch in _TR_CHARS) and tr_ratio < 0.004 and len(text) > 400:
        out.append((12, "Türkçe istenmiş ama metin Türkçe karakter içermiyor"))
    return out


def score(result: dict[str, Any], request: str) -> tuple[int, list[str]]:
    """(score, problems) for a generated deck (deep_research.generate_ai_pptx_presentation result)."""
    slides = [s for s in result.get("slides") or [] if isinstance(s, dict)]
    found: list[tuple[int, str]] = []
    if c := _count_issue(len(slides) + 1, request):
        found.append(c)
    for part in (_fullness_issues(slides), _variety_issues(slides), _title_issues(slides), _honesty_issues(slides, request), _topic_language_issues(slides, request)):
        found += part
    return max(0, 100 - sum(p for p, _ in found)), [m for _, m in found]

