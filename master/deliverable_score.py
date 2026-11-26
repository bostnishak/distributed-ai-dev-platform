"""Automatic quality score (0-100) for generated documents and workbooks, with the concrete problems found.

Used by the generation flows as a loop: build, score, and when the score is clearly below target feed the problems back to the model and
try again, keeping the best attempt. All checks are deterministic (no second model opinion), so a score means the same thing every time.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import doc_sanity
import doc_tables

TARGET = 85
_BRAND_RE = re.compile(r"(?:[A-ZÇĞİÖŞÜ0-9][\w'\u2019.-]*\s+){1,3}(?:Co\.|Ltd\.?|A\.Ş\.?|Inc\.?|LLC|Corp\.?)")
_GIVEN_AMOUNT_RE = re.compile(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+)\s*(?:TL|₺|lira)", re.IGNORECASE)
_UNIT_PRICE_RE = re.compile(r"(birim|sepet|fiyat|ortalama|günlük|saatlik|kişi\s+başı|adet|oran|kur\b|kdv)", re.IGNORECASE)
_EXTRA_COST_RE = re.compile(r"\b(sgk|vergi|kdv|stopaj|komisyon|prim|enflasyon|zam)\w*", re.IGNORECASE)
_BLANK = "[................]"
_IDENTITY_RE = re.compile(r"(kimlik|tc\b|t\.c|adres|iban|ada\b|parsel|plaka|imza|tarih|telefon|e-?posta|mahalle|sokak|no:|numara|vergi)", re.IGNORECASE)


def _texts(spec: dict[str, Any]) -> list[str]:
    out: list[str] = [spec.get("title", ""), spec.get("subtitle", "")]
    for b in spec["blocks"]:
        out += [b.get("text", ""), b.get("caption", ""), *b.get("items", []), *[c for r in b.get("rows", []) for c in r]]
    return [t for t in out if t]


def _amount(cell: str) -> float | None:
    """'125.000 TL' -> 125000.0, '1,38 TL' -> 1.38; None when the cell is not a plain amount."""
    m = re.fullmatch(r"\s*(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)\s*(?:TL|₺|\$|€|USD|EUR)?\s*", cell)
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None


def _implausible_amounts(spec: dict[str, Any]) -> list[str]:
    """Cells that are orders of magnitude below the rest of their column (a '1,38 TL' espresso machine next to 125.000 TL furniture)."""
    out: list[str] = []
    for b in spec["blocks"]:
        if b.get("type") != "table":
            continue
        for ci in range(len(b["headers"])):
            cells = [(r[ci], None if _UNIT_PRICE_RE.search(r[0]) else _amount(r[ci])) for r in b["rows"] if ci < len(r)]  # unit prices are small by nature
            values = [v for _, v in cells if v is not None]
            if len(values) >= 3 and max(values) >= 10000:
                out += [f"{c.strip()} ({b['rows'][i][0][:30]})" for i, (c, v) in enumerate(cells) if v is not None and v < max(values) / 500]
    return out


def _fabrication_issues(spec: dict[str, Any], request: str, texts: list[str]) -> tuple[int, list[str]]:
    """Invented dates and numbers that cannot be right: (penalty, problems)."""
    penalty, issues = 0, []
    now_year = datetime.now().year
    stale = {y for y in re.findall(r"\b(?:19|20)\d{2}\b", " ".join(texts)) if int(y) < now_year - 1 and y not in request}
    if stale:
        penalty += 10
        issues.append(f"uydurulmuş eski tarih var ({', '.join(sorted(stale))}); bugünün yılı {now_year}, kullanıcı vermediği tarihi yazma")
    if sane := doc_sanity.implausible_results(spec):
        penalty += 25
        issues.append("hesap sonuçları gerçekçi değil: " + "; ".join(sane[:3]))
    if oddities := _implausible_amounts(spec):
        penalty += 12
        issues.append("tabloda gerçekçi olmayan tutar var: " + "; ".join(oddities[:3]) + " (diğer kalemlerle aynı büyüklükte, gerçekçi bir tutar yaz)")
    brands = {m.group(0) for m in _BRAND_RE.finditer(" ".join(texts)) if m.group(0).lower() not in request.lower()}
    if brands:
        penalty += 12
        issues.append(f"kullanıcının vermediği marka/şirket adı uydurulmuş ({', '.join(sorted(brands)[:2])}); genel ad kullan (ör. 'Kahve Dükkanı')")
    given = {m.group(1) for m in _GIVEN_AMOUNT_RE.finditer(request)}
    body = " ".join(texts)
    absent = sorted(a for a in given if a not in body and a.replace(".", " ") not in body)
    if absent:
        penalty += min(30, 15 * len(absent))
        issues.append("kullanıcının verdiği tutar belgede geçmiyor: " + ", ".join(absent[:3]) + " TL (istekteki rakamı aynen yaz)")
    extras = sorted({r[0].strip() for b in spec["blocks"] if b.get("type") == "table" for r in b["rows"] if len(r) > 2 and "varsay" in r[2].lower() and _EXTRA_COST_RE.search(r[0]) and not _EXTRA_COST_RE.search(request)})
    if extras:
        penalty += 15
        issues.append("kullanıcının istemediği ek kalem/oran uydurulmuş: " + ", ".join(extras[:2]) + " (yalnızca verilen rakamlarla hesapla; SGK, vergi, KDV, prim vb. ekleme)")
    if layout := doc_tables.issues(spec):
        penalty += min(20, 8 * len(layout))
        issues += layout
    return penalty, issues


def score_document(spec: dict[str, Any], request: str, pages: int = 0, rendered_pages: int = 0) -> tuple[int, list[str]]:
    """(score, problems) for a parsed document spec (doc_spec.parse output)."""
    score, issues = 100, []
    texts = _texts(spec)
    blanks = [t for t in texts for _ in range(t.count(_BLANK)) if not (len(t) < 80 and _IDENTITY_RE.search(t))]
    if blanks:
        score -= min(45, 9 * len(blanks))
        issues.append(f"{len(blanks)} yerde sayı/bilgi boş bırakılmış ([....]); bunlar hesaplanmalı ya da varsayımla doldurulmalı")
    leaked = sorted({m.group(0) for t in texts for m in re.finditer(r"%?[a-z]{3,}_[a-z_]{2,}", re.sub(r"https?://\S+", " ", t))})
    if leaked:
        score -= 15
        issues.append(f"metne kod değişken adı sızmış ({', '.join(leaked[:3])}); gerçek değerini yaz")
    if any("{" in t and "}" in t for t in texts):
        score -= 15
        issues.append("metinde çözülmemiş {yer tutucu} kalmış")
    penalty, found = _fabrication_issues(spec, request, texts)
    score -= penalty
    issues += found
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
    broken = sum(1 for s in sheets for r in s["rows"] for c in r if isinstance(c, str) and re.search(r"\{[^{}]+\}|^=+\s*\{", c))
    if broken:
        score -= 25
        issues.append(f"{broken} hücrede çözülmemiş {{yer tutucu}}/bozuk formül var; formüller gerçek hücre adresleriyle (örn. =AVERAGE(B5:D5)) yazılmalı")
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
