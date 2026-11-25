"""Spreadsheet logic: row totals are formulas (qty * price), and unit prices / rates are never summed."""

from __future__ import annotations

import re
from typing import Any

from document_chart import to_number

_TOTAL_RE = re.compile(r"(toplam|tutar|total|amount|subtotal)", re.IGNORECASE)
_QTY_RE = re.compile(r"(adet|miktar|qty|quantity|sayı)", re.IGNORECASE)
_PRICE_RE = re.compile(r"(fiyat|price|birim|rate|oran|yüzde|%)", re.IGNORECASE)


def _col(headers: list[str], pattern: re.Pattern[str], skip: set[int]) -> int | None:
    return next((i for i, h in enumerate(headers) if i not in skip and pattern.search(h or "")), None)


def row_total_formula(headers: list[str], rows: list[list[Any]]) -> tuple[int, int, int] | None:
    """(total_col, qty_col, price_col) as 1-based indexes when the total column is qty * price in the data."""
    tot = _col(headers, _TOTAL_RE, set())
    qty = _col(headers, _QTY_RE, {tot} if tot is not None else set())
    price = _col(headers, _PRICE_RE, {x for x in (tot, qty) if x is not None})
    if tot is None or qty is None or price is None or not rows:
        return None
    for r in rows:
        q, p, t = (to_number(r[i]) if i < len(r) else None for i in (qty, price, tot))
        if q is None or p is None or t is None or abs(q * p - t) > 0.01 * max(1.0, abs(t)):
            return None
    return tot + 1, qty + 1, price + 1


def is_rate_column(header: str) -> bool:
    """Unit prices and rates make no sense as a SUM."""
    return bool(_PRICE_RE.search(header or "")) and not _TOTAL_RE.search(header or "")
