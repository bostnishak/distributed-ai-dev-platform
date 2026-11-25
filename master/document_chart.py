"""Chart and number helpers shared by the Word and PDF builders (no matplotlib: Pillow only)."""

from __future__ import annotations

import io
import math
import re
from typing import Any

import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

_SKIP_COLS_RE = re.compile(r"(toplam|total|ortalama|average|avg|sum)", re.IGNORECASE)
_RAW_COLS_RE = re.compile(r"(y[ıi]l|year|kod|\bno\b|\bid\b|tarih|date|telefon|phone|zip|posta)", re.IGNORECASE)
_PALETTE = ((79, 70, 229), (16, 185, 129), (245, 158, 11), (239, 68, 68), (14, 165, 233))
_MAX_SERIES, _MAX_CATS = 4, 12


def to_number(val: Any) -> float | None:
    """Parse '12.500', '12,500.50', '12500 TL', '%18' or a real number; None when the cell is text."""
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    raw = str(val or "").strip()
    s = re.sub(r"[%\s$€£₺]|TL|TRY|USD|EUR", "", raw, flags=re.IGNORECASE)
    if not s or not re.fullmatch(r"[+-]?[\d.,]+", s) or (len(s) > 1 and s.startswith("0") and s[1].isdigit()):
        return None
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", s) else s.replace(",", ".")
    elif "." in s and re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def format_cell(val: Any, header: str, lang: str) -> tuple[str, bool]:
    """Return (display text, is_numeric). Numeric cells get thousands separators in the report's language."""
    if _RAW_COLS_RE.search(header or ""):
        return str(val if val is not None else ""), False
    num = to_number(val)
    if num is None:
        return str(val if val is not None else ""), False
    is_pct = isinstance(val, str) and "%" in val
    txt = f"{num:,.1f}" if is_pct else (f"{num:,.0f}" if float(num).is_integer() else f"{num:,.2f}")
    if lang == "Türkçe":
        txt = txt.replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")
    return (txt + "%" if is_pct else txt), True


def chart_series(headers: list[str], rows: list[list[Any]]) -> tuple[list[str], list[tuple[str, list[float]]]] | None:
    """First column = categories; numeric columns (not totals) = series. None when there is nothing worth plotting."""
    if len(headers) < 2 or len(rows) < 2:
        return None
    cats = [str(r[0]) if r else "" for r in rows[:_MAX_CATS]]
    series: list[tuple[str, list[float]]] = []
    for ci in range(1, len(headers)):
        if _SKIP_COLS_RE.search(headers[ci]) or _RAW_COLS_RE.search(headers[ci]):
            continue
        vals = [to_number(r[ci]) if ci < len(r) else None for r in rows[:_MAX_CATS]]
        if all(v is not None for v in vals):
            series.append((str(headers[ci]), [float(v) for v in vals if v is not None]))
        if len(series) == _MAX_SERIES:
            break
    if not series:  # fall back to a totals column when it is the only numeric one
        for ci in range(1, len(headers)):
            vals = [to_number(r[ci]) if ci < len(r) else None for r in rows[:_MAX_CATS]]
            if all(v is not None for v in vals):
                return cats, [(str(headers[ci]), [float(v) for v in vals if v is not None])]
        return None
    return cats, series


def _font(path: str | None, size: int) -> Any:
    try:
        return ImageFont.truetype(path, size) if path else ImageFont.load_default()
    except OSError:
        return ImageFont.load_default()


def _nice_max(v: float) -> float:
    if v <= 0:
        return 1.0
    mag = 10 ** (len(str(int(v))) - 1)
    for step in (1, 2, 2.5, 5, 10):
        if v <= step * mag:
            return step * mag
    return 10 * mag


def render_bar_chart_png(headers: list[str], rows: list[list[Any]], title: str, fonts: tuple[str | None, str | None]) -> bytes | None:
    """Grouped bar chart as PNG bytes, or None when the table has no plottable numbers."""
    data = chart_series(headers, rows)
    if data is None:
        return None
    cats, series = data
    w, h = 1600, 820
    left, right, top, bottom = 150, 50, 130, 120
    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img)
    f_t, f_s, f_b = _font(fonts[1] or fonts[0], 34), _font(fonts[0], 24), _font(fonts[1] or fonts[0], 22)
    d.text((left, 28), title[:70], font=f_t, fill=(30, 41, 59))
    vmax = _nice_max(max(max(v) for _n, v in series))
    plot_w, plot_h = w - left - right, h - top - bottom
    for i in range(6):
        y = top + plot_h - plot_h * i / 5
        d.line([(left, y), (w - right, y)], fill=(226, 232, 240), width=2)
        label = f"{vmax * i / 5:,.0f}".replace(",", ".")
        d.text((left - 14 - d.textlength(label, font=f_s), y - 13), label, font=f_s, fill=(100, 116, 139))
    group_w = plot_w / len(cats)
    bar_w = min(90.0, group_w * 0.8 / len(series))
    for ci, cat in enumerate(cats):
        gx = left + ci * group_w + (group_w - bar_w * len(series)) / 2
        for si, (_name, vals) in enumerate(series):
            x0, bh = gx + si * bar_w, plot_h * vals[ci] / vmax
            d.rectangle([x0 + 2, top + plot_h - bh, x0 + bar_w - 2, top + plot_h], fill=_PALETTE[si % len(_PALETTE)])
            if len(series) == 1 and len(cats) <= 8:
                lab = f"{vals[ci]:,.0f}".replace(",", ".")
                d.text((x0 + bar_w / 2 - d.textlength(lab, font=f_s) / 2, top + plot_h - bh - 32), lab, font=f_s, fill=(51, 65, 85))
        lab = cat if len(cat) <= 12 else cat[:11] + "…"
        d.text((left + ci * group_w + group_w / 2 - d.textlength(lab, font=f_s) / 2, top + plot_h + 14), lab, font=f_s, fill=(51, 65, 85))
    d.line([(left, top + plot_h), (w - right, top + plot_h)], fill=(148, 163, 184), width=3)
    lx = left
    for si, (name, _v) in enumerate(series):
        d.rectangle([lx, h - 62, lx + 26, h - 36], fill=_PALETTE[si % len(_PALETTE)])
        d.text((lx + 36, h - 66), name[:24], font=f_b, fill=(51, 65, 85))
        lx += 60 + int(d.textlength(name[:24], font=f_b)) + 30
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


_THOUSAND_DOT_RE = re.compile(r"^[+-]?\d{1,3}(?:\.\d{3})+$")
_THOUSAND_COMMA_RE = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})+$")
_CURRENCY_RE = re.compile(r"(?:[$€£₺%\s\u00a0]+|\b(?:TL|TRY|USD|EUR|GBP)\b)", re.I)


def _normalize_numeric_str(s: str) -> str | None:
    if "." in s and "," in s:
        return s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    if "," in s:
        return s.replace(",", "") if _THOUSAND_COMMA_RE.match(s) else (s.replace(",", ".") if s.count(",") == 1 else None)
    if "." in s:
        return s.replace(".", "") if _THOUSAND_DOT_RE.match(s) else (s if s.count(".") == 1 else None)
    return s


def _coerce_excel_cell(val: Any) -> tuple[Any, str | None, bool]:
    """Coerce numeric strings like '12.500', '12,500.50', '12500 TL', '%18', '$1,200' to numbers."""
    if isinstance(val, bool) or not isinstance(val, (int, float, str)):
        return val, None, False
    if isinstance(val, int):
        return val, "#,##0", True
    if isinstance(val, float):
        return (val, "#,##0.00", True) if math.isfinite(val) else (str(val), None, False)
    raw = val.strip()
    is_pct, s = "%" in raw, _CURRENCY_RE.sub("", raw).strip()
    if not raw or (raw.isdigit() and len(raw) > 1 and raw.startswith("0")) or not s or not re.fullmatch(r"[+-]?[\d.,]+", s):
        return raw, None, False
    num_s = _normalize_numeric_str(s)
    try:
        parsed_f = float(num_s) if num_s is not None else math.nan
    except ValueError:
        return raw, None, False
    if not math.isfinite(parsed_f) or num_s is None:
        return raw, None, False
    if is_pct:
        return parsed_f / 100.0, "0.0%", True
    return (int(num_s), "#,##0", True) if "." not in num_s else (parsed_f, "#,##0.00", True)


def _row_height(values: list[str], col_widths: list[int], base: float = 20.0) -> float:
    lines = max((sum(max(1, math.ceil(len(p) / max(10, w - 3))) for p in (t.splitlines() or [""])) for t, w in zip(values, col_widths, strict=False)), default=1)
    return max(base, min(120.0, lines * 15.0 + 6.0))


def pdf_wrap_lines(text: str, max_w: float, font: fitz.Font, fontsize: float) -> list[str]:
    out: list[str] = []
    for para in re.sub(r"\*\*([^*]+)\*\*", r"\1", text or "").splitlines():
        if not para.strip():
            out.append("")
            continue
        cur = ""
        for word in para.split():
            trial = f"{cur} {word}".strip()
            if font.text_length(trial, fontsize=fontsize) <= max_w:
                cur = trial
            elif font.text_length(word, fontsize=fontsize) <= max_w:
                out.append(cur) if cur else None
                cur = word
            else:
                out.append(cur) if cur else None
                cur = ""
                for ch in word:
                    if font.text_length(cur + ch, fontsize=fontsize) > max_w and cur:
                        out.append(cur)
                        cur = ch
                    else:
                        cur += ch
        if cur:
            out.append(cur)
    return out or [""]
