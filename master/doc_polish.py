"""Deterministic clean-up of a parsed document against the user's request.

* Amounts the user gave ("25.000 TL", "2 ay") that the model left as a fill-in blank are written into that blank.
* Dates and rates the user never wrote were already blanked by doc_spec; here, filler lines that only announce a table are removed.
"""

from __future__ import annotations

import re
from typing import Any

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



def polish(blocks: list[dict[str, Any]], request: str) -> list[dict[str, Any]]:
    fill_deposit(blocks, request)
    fill_given_amounts(blocks, request)
    return drop_table_fillers(blocks)


_PCT_RE = re.compile(r"%\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*%")


def blank_invented_percentages(text: str, request: str) -> str:
    """Raw model text only (placeholders are not filled yet): a literal percentage that is not in the request becomes %[....]."""
    asked = {m.group(1) or m.group(2) for m in _PCT_RE.finditer(request)}
    return _PCT_RE.sub(lambda m: m.group(0) if (m.group(1) or m.group(2)) in asked else "%" + BLANK, text)


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
