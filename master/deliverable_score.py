"""Automatic quality score (0-100) for generated documents and workbooks, with the concrete problems found.

Used by the generation flows as a loop: build, score, and when the score is clearly below target feed the problems back to the model and
try again, keeping the best attempt. All checks are deterministic (no second model opinion), so a score means the same thing every time.
"""

from __future__ import annotations

import re
from typing import Any

TARGET = 85
_BLANK = "[................]"
_IDENTITY_RE = re.compile(r"(kimlik|tc\b|t\.c|adres|iban|ada\b|parsel|plaka|imza|tarih|telefon|e-?posta|mahalle|sokak|no:|numara|vergi)", re.IGNORECASE)


def _texts(spec: dict[str, Any]) -> list[str]:
    out: list[str] = [spec.get("title", ""), spec.get("subtitle", "")]
    for b in spec["blocks"]:
        out += [b.get("text", ""), b.get("caption", ""), *b.get("items", []), *[c for r in b.get("rows", []) for c in r]]
    return [t for t in out if t]


def score_document(spec: dict[str, Any], request: str, pages: int = 0, rendered_pages: int = 0) -> tuple[int, list[str]]:
    """(score, problems) for a parsed document spec (doc_spec.parse output)."""
    score, issues = 100, []
    texts = _texts(spec)
    blanks = [t for t in texts for _ in range(t.count(_BLANK)) if not _IDENTITY_RE.search(t)]
    if blanks:
        score -= min(45, 9 * len(blanks))
        issues.append(f"{len(blanks)} yerde sayı/bilgi boş bırakılmış ([....]); bunlar hesaplanmalı ya da varsayımla doldurulmalı")
    if any("{" in t and "}" in t for t in texts):
        score -= 15
        issues.append("metinde çözülmemiş {yer tutucu} kalmış")
    words = sum(len(t.split()) for t in texts)
    wants_calc = bool(re.search(r"hesap|toplam|başa\s*baş|maliyet|gelir|bütçe|yatırım|oran|tutar", request, re.IGNORECASE))
    kinds = {b["type"] for b in spec["blocks"]}
    if wants_calc and "table" not in kinds:
        score -= 15
        issues.append("hesap istenmesine rağmen tablo yok")
    if pages and words < 140 * pages:
        score -= 12
        issues.append(f"{pages} sayfa için metin çok kısa ({words} kelime)")
    if pages and rendered_pages > pages:
        score -= 12
        issues.append(f"belge {rendered_pages} sayfa oldu, istenen {pages}")
    if re.search(r"\bBu doküman\b|\bbu belge[^.]{0,40}sunmaktadır", " ".join(texts[:4]), re.IGNORECASE):
        score -= 6
        issues.append("belgeyi anlatan giriş cümlesi var; doğrudan içerikle başlanmalı")
    if sum(1 for b in spec["blocks"] if b["type"] in ("para", "numbered", "bullets", "table")) < 4:
        score -= 10
        issues.append("içerik bölümleri çok az")
    return max(score, 0), issues


def score_workbook(spec: dict[str, Any], request: str) -> tuple[int, list[str]]:
    """(score, problems) for a parsed workbook spec (xlsx_builder.parse_spec output)."""
    score, issues = 100, []
    sheets = spec["sheets"]
    formulas = sum(len(s.get("formulas", [])) + len(s.get("col_formulas", {})) for s in sheets)
    if formulas == 0:
        score -= 30
        issues.append("hiç formül yok; hesaplanan sütunlar formül olmalı")
    if not any(s.get("chart") for s in sheets):
        score -= 15
        issues.append("grafik yok")
    if any(len(s["rows"]) < 5 for s in sheets):
        score -= 10
        issues.append("bazı sayfalarda 5'ten az satır var")
    if re.search(r"bütçe", request, re.IGNORECASE) and not any(s.get("summary") for s in sheets):
        score -= 20
        issues.append("bütçe istenmiş ama toplam/bütçe/kalan satırları yok")
    if re.search(r"kar[sş]ıla[sş]t[ıi]r", request, re.IGNORECASE) and len(sheets) > 1 and not spec.get("comparison"):
        score -= 15
        issues.append("karşılaştırma istenmiş ama karşılaştırma sayfası yok")
    named = re.search(r"\(([^()]{3,80}(?:,|\bve\b)[^()]{2,80})\)", request)
    titles = " ".join(str(s.get("name", "")) for s in sheets).lower()
    missing = [n for n in re.split(r",|\bve\b", named.group(1)) if len(n.strip()) >= 3 and n.strip().lower()[:5] not in titles] if named else []
    if missing and len(sheets) > 1:
        score -= 20
        issues.append(f"istekte adı geçen birimler için ayrı sayfa yok: {', '.join(m.strip() for m in missing)}")
    headers = [h.lower() for s in sheets for h in s["headers"]]
    if any(h in ("", "sütun 1", "column1") for h in headers):
        score -= 10
        issues.append("anlamsız sütun başlığı var")
    if len(sheets) == 1 and re.search(r"(\d+|üç|iki|dört)\s*(şantiye|şube|bölüm|sayfa|departman|ürün)", request, re.IGNORECASE):
        score -= 10
        issues.append("birden fazla birim istenmiş ama tek sayfa var")
    return max(score, 0), issues


def feedback(issues: list[str]) -> str:
    """Text appended to the request on a retry so the model fixes exactly what was found."""
    return "\n\n[Önceki denemede şu sorunlar vardı, bu sefer hepsini gider:\n" + "\n".join(f"- {i}" for i in issues) + "]"


def score_deck(result: dict[str, Any], request: str) -> tuple[int, list[str]]:
    """(score, problems) for a generated deck (deep_research.generate_ai_pptx_presentation result); the rubric lives in deck_score."""
    import deck_score

    return deck_score.score(result, request)
