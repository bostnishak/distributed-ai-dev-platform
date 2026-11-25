"""Plausibility checks on the calculated results of a generated document (wrong units make a payback of 1.624.427 years)."""

from __future__ import annotations

import re
from typing import Any

_NUM_RE = re.compile(r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?|-?\d+(?:,\d+)?")
_PAYBACK_RE = re.compile(r"(geri\s*ödeme|amorti|payback)", re.IGNORECASE)
_PERCENT_RE = re.compile(r"(oran|verim|marj|yüzde|büyüme)", re.IGNORECASE)
_HUGE = 5e9


def _value(cell: str) -> float | None:
    m = _NUM_RE.search(cell)
    return float(m.group(0).replace(".", "").replace(",", ".")) if m else None


def _payback_ok(text: str, value: float) -> bool:
    """Payback within a believable range for its unit (years 0.1-60, months 1-720; unit unknown: 0.1-720)."""
    low = text.lower()
    lo, hi = (1.0, 720.0) if re.search(r"\bay\b", low) and "yıl" not in low else (0.1, 60.0) if "yıl" in low else (0.1, 720.0)
    return lo <= value <= hi


def _money(rows: list[list[str]], words: str) -> float | None:
    for r in rows:
        if len(r) > 1 and re.search(words, r[0], re.IGNORECASE) and (v := _value(r[1])) is not None:
            return v * (12 if re.search(r"aylık", r[0], re.IGNORECASE) else 1)
    return None


def _ratio_issue(rows: list[list[str]]) -> str:
    """Yearly income more than three times the investment means the model mixed units (kW/MW, TL/bin TL)."""
    invest, income = _money(rows, r"(toplam\s+)?yatırım\s+(tutar|maliyet)"), _money(rows, r"(net\s+)?(gelir|getiri|kâr|kar)\b")
    if invest and income and invest > 0 and income / invest > 3:
        return f"yıllık gelir/getiri ({income:,.0f}) yatırımın ({invest:,.0f}) 3 katından fazla çıkmış; birimler karışmış olabilir (kW↔MW, TL↔bin TL)"
    return ""


def _checks(label: str, cell: str, value: float) -> str:
    if _PAYBACK_RE.search(label) and not _payback_ok(label + " " + cell, value):
        return f"{label.strip()} = {cell.strip()} gerçekçi değil (birimleri kontrol et: kW↔MW, TL↔bin TL, aylık↔yıllık)"
    if _PERCENT_RE.search(label) and "%" in cell and not 0 <= value <= 100:
        return f"{label.strip()} = {cell.strip()} yüzde olarak gerçekçi değil"
    if abs(value) >= _HUGE and re.search(r"TL|₺", label + cell):
        return f"{label.strip()} = {cell.strip()} aşırı büyük; birim hatası olabilir"
    if value == 0 and re.search(r"(net\s+)?(kar|kâr)\b", label, re.IGNORECASE):
        return f"{label.strip()} = 0; gelir ve gider değerleri gözden geçirilmeli (hesap mantık hatası)"
    return ""


def implausible_results(spec: dict[str, Any]) -> list[str]:
    """Problems in the 'hesaplanan' rows of the calculation table and in any 2-column label/value table."""
    out: list[str] = []
    for b in spec["blocks"]:
        if b.get("type") != "table":
            continue
        for row in b["rows"]:
            value = _value(row[1]) if len(row) > 1 else None
            if value is not None and (msg := _checks(row[0], row[1], value)):
                out.append(msg)
        if msg := _ratio_issue(b["rows"]):
            out.append(msg)
    return out
