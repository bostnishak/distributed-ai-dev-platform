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


def _checks(label: str, cell: str, value: float) -> str:
    if _PAYBACK_RE.search(label) and ("yıl" in label.lower() or "yıl" in cell.lower()) and not 0.05 <= value <= 60:
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
    return out
