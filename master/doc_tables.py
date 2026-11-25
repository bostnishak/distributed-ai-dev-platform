"""Tables and charts of generated documents must agree with themselves: one number format per column, units once, honest totals, charts that plot the table."""

from __future__ import annotations

import re
from typing import Any

_CELL_RE = re.compile(r"^\s*([-+]?\d[\d.,]*)\s*(%|[^\d\s].{0,12})?\s*$")
_SHARE_HEAD_RE = re.compile(r"(pay|dağılım|yüzde|%)", re.IGNORECASE)
_TOTAL_RE = re.compile(r"^\s*(genel\s+)?(toplam|total|sum)\b", re.IGNORECASE)


def parse_number(text: str) -> float | None:
    """Turkish or English formatted number -> float ('1.250,5', '1,250.5', '125000', '1.38')."""
    s = text.strip()
    if not re.fullmatch(r"[-+]?\d[\d.,]*", s):
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(".", "").replace(",", ".") if s.count(",") == 1 else s.replace(",", "")
    elif s.count(".") > 1 or re.fullmatch(r"[-+]?\d{1,3}\.\d{3}", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def fmt(value: float, decimals: int) -> str:
    text = f"{value:,.{decimals}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return text


def _split(cell: str) -> tuple[float, str] | None:
    m = _CELL_RE.match(cell or "")
    num = parse_number(m.group(1)) if m else None
    return (num, (m.group(2) or "").strip()) if m and num is not None else None


def _decimals(values: list[float]) -> int:
    """Digits after the comma needed by the most precise value in the column (0-2)."""
    digits = 0
    for v in values:
        frac = f"{v:.2f}".split(".")[1].rstrip("0")
        digits = max(digits, len(frac))
    return digits


def _normalise_column(rows: list[list[str]], ci: int, header: str) -> None:
    parts = [_split(r[ci]) for r in rows]
    numeric = [p for p in parts if p]
    if len(numeric) < 2 or len(numeric) < 0.6 * len(rows):
        return
    decimals = _decimals([n for n, _ in numeric])
    units = {u for _, u in numeric}
    in_header = bool(units) and all(u and u.lower() in header.lower() for u in units)
    unit = units.pop() if len(units) == 1 and not in_header else None
    for r, p in zip(rows, parts, strict=True):
        if p:
            r[ci] = fmt(p[0], decimals) + (f" {p[1]}" if p[1] and not in_header and (unit or p[1]) else "")


def _numeric_column(table: dict[str, Any]) -> int | None:
    for ci in range(1, len(table["headers"])):
        if all((v := parse_number(r[ci].split(" ")[0])) is not None and v >= 0 for r in table["rows"]):
            return ci
    return None


def _sync_chart(chart: dict[str, Any], tables: list[dict[str, Any]]) -> None:
    """A chart whose labels are a table's first column plots that table's first numeric column (re-typed model numbers are guesses)."""
    labels = [lab.strip().lower() for lab in chart["labels"]]
    for t in tables:
        ci = _numeric_column(t)
        if ci is not None and [r[0].strip().lower() for r in t["rows"]] == labels:
            chart["values"] = [parse_number(r[ci].split(" ")[0]) for r in t["rows"]]
            chart["title"] = chart["title"] or t["headers"][ci]
            return


def normalise(blocks: list[dict[str, Any]]) -> None:
    """Rectangular tables, one number format per column, no empty cells, charts equal to their tables."""
    tables = [b for b in blocks if b.get("type") == "table"]
    for b in tables:
        b.setdefault("headers", [""] * max((len(r) for r in b["rows"]), default=0))
        width = len(b["headers"])
        b["rows"] = [[(c or "").strip() or "—" for c in (list(r) + [""] * width)[:width]] for r in b["rows"]]
        for ci in range(width):
            _normalise_column(b["rows"], ci, b["headers"][ci])
    for b in blocks:
        if b.get("type") == "chart":
            _sync_chart(b, tables)


def is_total_row(row: list[str]) -> bool:
    return bool(row) and bool(_TOTAL_RE.search(row[0]))


def issues(spec: dict[str, Any]) -> list[str]:
    """Problems a reader would notice: duplicate headers, one-row tables, shares that do not add to 100, unreadable charts."""
    out: list[str] = []
    for b in spec["blocks"]:
        if b.get("type") == "table":
            heads = [h.strip().lower() for h in b["headers"]]
            if len(set(heads)) < len(heads) or any(not h for h in heads):
                out.append("tabloda tekrar eden ya da boş sütun başlığı var")
            if len(b["rows"]) < 2:
                out.append("tabloda tek satır var; tablo en az iki satır olmalı")
            for ci, h in enumerate(b["headers"]):
                vals = [parse_number(r[ci].split(" ")[0]) for r in b["rows"] if not is_total_row(r)]
                if _SHARE_HEAD_RE.search(h) and len(vals) >= 3 and all(v is not None and 0 <= v <= 100 for v in vals) and not 98.5 <= sum(vals) <= 101.5:  # type: ignore[arg-type]
                    out.append(f"'{h}' sütunundaki paylar %100 etmiyor (toplam {sum(vals):g})")  # type: ignore[arg-type]
        elif b.get("type") == "chart" and (len(set(b["labels"])) < len(b["labels"]) or max(b["values"]) == 0):
            out.append("grafikte tekrar eden etiket ya da hepsi sıfır değer var")
    return out
