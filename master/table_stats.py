"""Exact figures for uploaded tables, computed in code, so the model quotes them instead of doing arithmetic itself.

Besides column totals this reports data-quality problems row by row (blank, non-numeric, negative values) and group totals
(e.g. revenue per seller) computed only from the valid rows, so the answer can say exactly which rows were left out.
"""

from __future__ import annotations

import re

from document_chart import to_number
from document_formulas import _PRICE_RE, _QTY_RE, _col

_MAX_ROWS = 5000


def _parse(text: str) -> tuple[list[str], list[list[str]]] | None:
    lines = [ln for ln in text.splitlines() if ln.count(" | ") >= 1]
    if len(lines) < 3:
        return None
    rows = [[c.strip() for c in ln.split(" | ")] for ln in lines[:_MAX_ROWS]]
    width = len(rows[0])
    body = [r for r in rows[1:] if len(r) == width]
    return (rows[0], body) if width >= 2 and len(body) >= 2 else None


def _fmt(x: float) -> str:
    text = f"{x:,.2f}".rstrip("0").rstrip(".")
    return text.replace(",", " ")


def _numeric_columns(headers: list[str], rows: list[list[str]]) -> dict[int, list[float | None]]:
    """Columns where most cells are numbers; bad cells stay None so they can be reported."""
    cols: dict[int, list[float | None]] = {}
    for ci in range(len(headers)):
        vals = [to_number(r[ci]) for r in rows]
        if sum(v is not None for v in vals) >= max(2, int(0.5 * len(rows))):
            cols[ci] = vals
    return cols


def _who(row: list[str]) -> str:
    """The first two text cells identify a row for the user (e.g. seller and product)."""
    return " / ".join(c for c in row[:2] if c and to_number(c) is None) or "satır"


def _problems(headers: list[str], rows: list[list[str]], numeric: dict[int, list[float | None]]) -> tuple[list[str], set[int]]:
    notes, bad_rows = [], set()
    for ci, vals in numeric.items():
        for ri, v in enumerate(vals):
            cell = rows[ri][ci]
            if v is None:
                notes.append(f"satır {ri + 2} ({_who(rows[ri])}): '{headers[ci]}' {'boş' if not cell else f'sayı değil ({cell})'}")
                bad_rows.add(ri)
            elif v < 0:
                notes.append(f"satır {ri + 2} ({_who(rows[ri])}): '{headers[ci]}' negatif ({cell})")
                bad_rows.add(ri)
    return notes, bad_rows


def _group_totals(headers: list[str], rows: list[list[str]], values: list[float | None], label: str) -> list[str]:
    out: list[str] = []
    for ci, h in enumerate(headers):
        names = [r[ci] for r in rows]
        distinct = set(names)
        if any(to_number(n) is not None for n in names) or not 2 <= len(distinct) <= max(2, len(rows) // 2) or len(distinct) > 15:
            continue
        sums = {k: sum(v for r, v in zip(rows, values, strict=True) if r[ci] == k and v is not None) for k in distinct}
        ranked = sorted(sums.items(), key=lambda kv: -kv[1])
        out.append(f"- {h} bazında {label}: " + "; ".join(f"{k}: {_fmt(v)}" for k, v in ranked) + f"  (en yüksek: {ranked[0][0]})")
    return out


def summary(extracted_text: str) -> str:
    """A 'computed summary' block for a table-like text, or '' when the text is not a table."""
    parsed = _parse(extracted_text)
    if parsed is None:
        return ""
    headers, rows = parsed
    numeric = _numeric_columns(headers, rows)
    problems, bad = _problems(headers, rows, numeric)
    out: list[str] = []
    for ci, vals in numeric.items():
        good = [v for r, v in zip(rows, vals, strict=True) if v is not None and v >= 0]
        if good:
            out.append(f"- {headers[ci]} (geçerli {len(good)} satır): toplam {_fmt(sum(good))}, ortalama {_fmt(sum(good) / len(good))}, en küçük {_fmt(min(good))}, en büyük {_fmt(max(good))}")
    qty = _col(headers, _QTY_RE, set())
    price = _col(headers, _PRICE_RE, {qty} if qty is not None else set())
    metric: list[float | None] | None = None
    label = ""
    if qty in numeric and price in numeric:
        metric = [None if i in bad else numeric[qty][i] * numeric[price][i] for i in range(len(rows))]  # type: ignore[operator]
        label = f"{headers[qty]} x {headers[price]}"
        valid = [m for m in metric if m is not None]
        out.append(f"- {label} (yalnızca sorunsuz satırlar çarpılıp toplanır): toplam {_fmt(sum(valid))} ({len(valid)} satır)")
    elif numeric:
        metric = [None if i in bad else v for i, v in enumerate(numeric[max(numeric)])]
        label = headers[max(numeric)]
    if metric:
        out += _group_totals(headers, rows, metric, label)
    if problems:
        out.append(f"- VERİ SORUNLARI ({len(problems)}): " + "; ".join(problems[:20]) + " → bu satırlar yukarıdaki çarpım/grup toplamlarına dahil EDİLMEDİ.")
    if not out:
        return ""
    return f"\n\n--- Koddan HESAPLANMIŞ tablo özeti ({len(rows)} satır; bu rakamları aynen kullan, kendin hesaplama, veri sorunlarını kullanıcıya açıkça söyle) ---\n" + "\n".join(out)


def looks_tabular(text: str) -> bool:
    return bool(re.search(r" \| ", text))
