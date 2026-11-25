"""Deterministic clean-up of a parsed document against the user's request.

* Amounts the user gave ("25.000 TL", "2 ay") that the model left as a fill-in blank are written into that blank.
* Dates and rates the user never wrote were already blanked by doc_spec; here, filler lines that only announce a table are removed.
"""

from __future__ import annotations

import re
from typing import Any

import doc_tables

BLANK = "[................]"
_AMOUNT_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)\s*(TL|₺|lira|ay|gün|yıl|adet|kişi|%)", re.IGNORECASE)
_TABLE_FILLER_RE = re.compile(r"\b(tablo\w*|özet\w*)\b[^.]{0,40}\.$", re.IGNORECASE)


def _units(unit: str) -> str:
    u = unit.lower()
    return r"(?:TL|₺|lira)" if u in ("tl", "₺", "lira") else re.escape(u)


def _fill(pattern: re.Pattern[str], num: str, text: str) -> str:
    return pattern.sub(lambda m: f"{num}{m.group(1)}{m.group(2)}", text, count=1)


def _fill_table(block: dict[str, Any], pattern: re.Pattern[str], num: str) -> bool:
    """Fill the first matching blank inside a table cell; True when one was filled."""
    for row in block.get("rows", []):
        for ci, cell in enumerate(row):
            if pattern.search(cell):
                row[ci] = _fill(pattern, num, cell)
                return True
    return False


def fill_given_amounts(blocks: list[dict[str, Any]], request: str) -> None:
    """Write each amount from the request into the first matching blank, e.g. '[....] TL' <- '25.000 TL'."""
    for num, unit in dict.fromkeys(_AMOUNT_RE.findall(request)):
        flat = " ".join(b.get("text", "") + " ".join(b.get("items", [])) for b in blocks)
        if re.search(rf"{re.escape(num)}\s*{_units(unit)}", flat, re.IGNORECASE):
            continue  # already in the document
        pattern = re.compile(rf"\[\.{{6,}}\](\s*)({_units(unit)})", re.IGNORECASE)
        for b in blocks:
            if "text" in b and pattern.search(b["text"]):
                b["text"] = _fill(pattern, num, b["text"])
                break
            hit = next((i for i, item in enumerate(b.get("items", [])) if pattern.search(item)), None)
            if hit is not None:
                b["items"][hit] = _fill(pattern, num, b["items"][hit])
                break
            if _fill_table(b, pattern, num):
                break


def drop_table_fillers(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A short paragraph that only announces the following table ('Sözleşme ile ilgili finansal özet tablosu.') carries no content."""
    keep = []
    for i, b in enumerate(blocks):
        nxt = blocks[i + 1]["type"] if i + 1 < len(blocks) else ""
        if b["type"] == "para" and len(b["text"]) <= 80 and nxt == "table" and _TABLE_FILLER_RE.search(b["text"]):
            continue
        keep.append(b)
    return keep


_DEPOSIT_RE = re.compile(r"depozito\w*[^.]{0,40}?(\d+)\s*(?:aylık|ay)\s*kira", re.IGNORECASE)
_RENT_RE = re.compile(r"(?:aylık\s+)?kira\w*[^.\d]{0,30}?(\d{1,3}(?:\.\d{3})+|\d+)\s*(?:TL|₺|lira)", re.IGNORECASE)


def fill_deposit(blocks: list[dict[str, Any]], request: str) -> None:
    """'depozito 2 aylık kira' + 'aylık kira 25.000 TL' -> the deposit blank gets 50.000 TL."""
    dep, rent = _DEPOSIT_RE.search(request), _RENT_RE.search(request)
    if not dep or not rent:
        return
    total = int(dep.group(1)) * int(rent.group(1).replace(".", ""))
    value = f"{total:,}".replace(",", ".")
    pattern = re.compile(r"(depozito[^.\[]{0,120}?)\[\.{6,}\](\s*)(TL|₺|lira)", re.IGNORECASE)
    for b in blocks:
        for key in ("text", "caption"):
            if key in b and pattern.search(b[key]):
                b[key] = pattern.sub(lambda m: f"{m.group(1)}{value}{m.group(2)}{m.group(3)}", b[key], count=1)
                return
        for ri, row in enumerate(b.get("rows", [])):
            if row and re.search(r"depozito", " ".join(row), re.IGNORECASE):
                b["rows"][ri] = [re.sub(r"\[\.{6,}\](\s*)(TL|₺|lira)?", lambda m: f"{value}{m.group(1)}{m.group(2) or 'TL'}", c, count=1) for c in row]
                return



_DUP_UNIT_RE = re.compile(r"(?<!\w)([^\s\d]*[A-Za-z$%€₺/][^\s\d]*)\s+\1(?!\w)")
_SIGNED_RE = re.compile(r"(sözleşme|sozlesme|imza|taahhüt|dilekçe|dilekce|mektup|protokol|tutanak|vekalet|contract|agreement)", re.IGNORECASE)


def _dedupe_units(blocks: list[dict[str, Any]]) -> None:
    """'1.850 MW MW' / '1,35 $/kW $/kW' -> one unit (the model repeats the unit already in the column header)."""
    for b in blocks:
        for row in b.get("rows", []):
            row[:] = [_DUP_UNIT_RE.sub(r"\1", c) for c in row]


def polish(blocks: list[dict[str, Any]], request: str) -> list[dict[str, Any]]:
    fill_deposit(blocks, request)
    fill_given_amounts(blocks, request)
    _dedupe_units(blocks)
    blocks = _drop_repeated_tables(blocks)
    doc_tables.normalise(blocks)
    fix_totals(blocks)
    if not _SIGNED_RE.search(request):
        blocks = [b for b in blocks if b["type"] != "signature"]  # an unrequested signature block only adds invented names and dates
    return drop_table_fillers(blocks)


_PCT_RE = re.compile(r"%\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*%")


_ASSUMED_RE = re.compile(r"(varsay|tahmin|yaklaşık|ortalama|sektör|tipik|assum|estimate|approx)", re.IGNORECASE)


def blank_invented_percentages(text: str, request: str) -> str:
    """Raw model text only (placeholders are not filled yet): a literal percentage that is neither in the request nor presented as an
    assumption/estimate becomes %[....]; a labelled assumption stays, so plans keep their working rates."""
    asked = {m.group(1) or m.group(2) for m in _PCT_RE.finditer(request)}

    def keep(m: re.Match[str]) -> str:
        near = text[max(0, m.start() - 60) : m.end() + 25]
        return m.group(0) if (m.group(1) or m.group(2)) in asked or _ASSUMED_RE.search(near) else "%" + BLANK

    return _PCT_RE.sub(keep, text)


_DAILY_RE = re.compile(r"günlük\s+(\d{1,5})\s+[\wçğıöşü]+(?:\s+ve)?\s+(?:ortalama\s+)?(?:sepet\s+)?(\d{1,3}(?:\.\d{3})+|\d+)\s*(?:TL|₺|lira)", re.IGNORECASE)


def request_facts(request: str) -> str:
    """Obvious derived numbers from the request, computed here and handed to the model as fixed facts (e.g. 120 x 85 TL x 30 days)."""
    facts = []
    if m := _DAILY_RE.search(request):
        qty, price = int(m.group(1)), int(m.group(2).replace(".", ""))
        daily = qty * price
        fmt = lambda n: f"{n:,}".replace(",", ".")  # noqa: E731
        facts.append(f"günlük ciro = {qty} x {fmt(price)} TL = {fmt(daily)} TL; aylık ciro (30 gün) = {fmt(daily * 30)} TL; yıllık ciro (12 ay) = {fmt(daily * 360)} TL")
    return ("\n\n[Kesin hesaplanmış değerler, aynen kullan (kendin yeniden hesaplama): " + "; ".join(facts) + "]") if facts else ""


_TOTAL_RE = re.compile(r"^\s*(genel\s+)?(toplam|total|sum)\b", re.IGNORECASE)


def fix_totals(blocks: list[dict[str, Any]]) -> None:
    """A 'Toplam' row must equal the sum of the rows above it: the model's mental addition is replaced by the real sum."""
    from deliverable_score import _amount
    from doc_calc import fmt_number

    for b in blocks:
        rows = b.get("rows") or []
        if b.get("type") != "table" or len(rows) < 3 or not _TOTAL_RE.search(rows[-1][0]):
            continue
        for ci in range(1, len(rows[-1])):
            total = _amount(rows[-1][ci])
            parts = [v for r in rows[:-1] if ci < len(r) and (v := _amount(r[ci])) is not None]
            if total is None or len(parts) < 2 or abs(sum(parts) - total) <= max(0.5, total * 0.002):
                continue
            unit = re.sub(r"[\d.,\s]", "", rows[-1][ci])
            rows[-1][ci] = fmt_number(sum(parts), unit)


def _drop_repeated_tables(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The calculation table is sometimes written twice; the second identical table is dropped."""
    seen: list[Any] = []
    out = []
    for b in blocks:
        key = (tuple(b.get("headers", ())), tuple(map(tuple, b["rows"]))) if b.get("type") == "table" else None
        if key is not None and key in seen:
            continue
        if key is not None:
            seen.append(key)
        out.append(b)
    return out
