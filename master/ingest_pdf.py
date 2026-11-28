"""Messy PDFs into ordered, located text: columns read in order, scanned pages read by OCR, tables and formulas kept.

Every block carries its page and box (in PDF points), so an answer can say where it comes from. A page without a text
layer is rendered and read by OCR; when it reads badly it is tried turned by 90 degrees (a sideways scan).
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass
from typing import Any

import pymupdf

import ocr_engine

_DPI = 200
_SCALE = 72 / _DPI
_MIN_TEXT = 20
_WIDE_SHARE = 0.6  # a block wider than this share of the page belongs to no column
_MATH_RE = re.compile(r"[∑∫√∂∆∇≤≥≠≈±\u00d7÷∞πθλμσ^]|\b\w+\s*=\s*[-\d\w(].*[+\-*/^()]")
_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Block:
    page: int
    kind: str  # "metin" | "tablo" | "formül" | "ocr"
    text: str
    box: tuple[float, float, float, float]


def _clean(text: str) -> str:
    return text.replace("\u00a0", " ").replace("\u00ad", "-").strip()


def _reading_order(blocks: list[Block], width: float) -> list[Block]:
    """Top to bottom, but within a band of side-by-side columns each column is finished before the next."""
    ordered: list[Block] = []
    band: list[Block] = []

    def flush() -> None:
        columns: list[list[Block]] = []
        for block in sorted(band, key=lambda b: b.box[0]):
            for column in columns:
                if block.box[0] < max(b.box[2] for b in column) - 4:
                    column.append(block)
                    break
            else:
                columns.append([block])
        for column in columns:
            ordered.extend(sorted(column, key=lambda b: b.box[1]))
        band.clear()

    for block in sorted(blocks, key=lambda b: (b.box[1], b.box[0])):
        if block.kind == "tablo" or block.box[2] - block.box[0] > width * _WIDE_SHARE:  # these span or bridge the columns
            flush()
            ordered.append(block)
        else:
            band.append(block)
    flush()
    return ordered


def _markdown(rows: list[list[Any]]) -> str:
    """A merged cell comes back empty: it takes the value of the cell it was merged with (above, or to the left)."""
    cells = [[("" if c is None else _clean(str(c).replace("\n", " "))) if c is not None else None for c in row] for row in rows]
    for r, row in enumerate(cells):
        for c, value in enumerate(row):
            if value is None:
                above = cells[r - 1][c] if r > 1 else None
                row[c] = (row[c - 1] if c and row[c - 1] else above) or ""
    width = max((len(row) for row in cells), default=0)
    cells = [row + [""] * (width - len(row)) for row in cells]
    used = [i for i in range(width) if any(row[i] for row in cells)]
    if not used:
        return ""
    cells, width = [[row[i] for i in used] for row in cells], len(used)
    return "\n".join(["| " + " | ".join(cells[0]) + " |", "|" + "---|" * width, *("| " + " | ".join(row) + " |" for row in cells[1:])])


def _rules(page: Any) -> list[tuple[float, float, float]]:
    """The horizontal ruling lines of the page as (y, left, right)."""
    found = []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] == "l" and abs(item[1].y - item[2].y) < 1:
                found.append((item[1].y, min(item[1].x, item[2].x), max(item[1].x, item[2].x)))
            elif item[0] == "re":
                box = item[1]
                found += [(box.y0, box.x0, box.x1), (box.y1, box.x0, box.x1)]
    return found


def _merged_above(box: tuple[float, ...], rules: list[tuple[float, float, float]]) -> bool:
    """A row boundary is ruled across other columns here, but not above this cell: the cell continues the one above."""
    level = [(left, right) for y, left, right in rules if abs(y - box[1]) <= 4]
    middle = (box[0] + box[2]) / 2
    return bool(level) and not any(left - 1 <= middle <= right + 1 for left, right in level)


def _rows(table: Any, rules: list[tuple[float, float, float]]) -> list[list[Any]]:
    """The cell texts, with None where a cell belongs to a merged one."""
    return [
        [None if box is None or (not value and _merged_above(box, rules)) else value for value, box in zip(values, row.cells, strict=False)]
        for values, row in zip(table.extract(), table.rows, strict=False)
    ]


def _tables(page: Any, number: int) -> list[Block]:
    found, rules = [], _rules(page)
    for table in page.find_tables().tables:
        text = _markdown(_rows(table, rules))
        if text:
            found.append(Block(number, "tablo", text, tuple(round(v, 1) for v in table.bbox)))
    return found


def _inside(box: tuple[float, ...], outer: tuple[float, ...]) -> bool:
    x, y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return outer[0] <= x <= outer[2] and outer[1] <= y <= outer[3]


def _text_blocks(page: Any, number: int, tables: list[Block]) -> list[Block]:
    found = []
    for x0, y0, x1, y1, text, _no, kind in page.get_text("blocks"):
        cleaned = _clean(text)
        box = (round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1))
        if kind == 0 and cleaned and not any(_inside(box, t.box) for t in tables):
            found.append(Block(number, "formül" if _MATH_RE.search(cleaned) and len(cleaned) < 200 else "metin", cleaned, box))
    return found


def _ocr_lines(page: Any, turn: int) -> list[ocr_engine.Line]:
    return ocr_engine.read(page.get_pixmap(matrix=pymupdf.Matrix(_DPI / 72, _DPI / 72).prerotate(turn)).tobytes("png"))


def _quality(lines: list[ocr_engine.Line]) -> float:
    """Confidently read characters in lines that are wider than tall (a sideways page gives short, tall boxes)."""
    return sum(len(line.text) * line.score for line in lines if (line.box[2] - line.box[0]) > (line.box[3] - line.box[1]))


def _scanned(page: Any, number: int) -> list[Block]:
    best = _ocr_lines(page, 0)
    if _quality(best) < _MIN_TEXT * 2:
        for turn in (90, 270):
            other = _ocr_lines(page, turn)
            if _quality(other) > _quality(best):
                best = other
    return [Block(number, "ocr", line.text, tuple(round(v * _SCALE, 1) for v in line.box)) for line in best]


def blocks(raw: bytes, max_pages: int = 200) -> tuple[list[Block], list[str]]:
    """(blocks in reading order, warnings). A scanned page without an OCR model is reported, never silently skipped."""
    found: list[Block] = []
    warnings: list[str] = []
    with pymupdf.open(stream=raw, filetype="pdf") as document:
        for number, page in enumerate(document, 1):
            if number > max_pages:
                warnings.append(f"Yalnız ilk {max_pages} sayfa okundu.")
                break
            tables = _tables(page, number)
            text = _text_blocks(page, number, tables)
            if sum(len(b.text) for b in (*text, *tables)) >= _MIN_TEXT or not page.get_images():
                found += _reading_order([*text, *tables], page.rect.width)
                continue
            try:
                found += _scanned(page, number)
            except ocr_engine.OcrUnavailable as exc:
                warnings.append(f"Sayfa {number} taranmış görüntü ve okunamadı: {exc}")
    return found, warnings


def markdown(raw: bytes) -> str:
    found, warnings = blocks(raw)
    out: list[str] = []
    page = 0
    for block in found:
        if block.page != page:
            page = block.page
            out.append(f"## Sayfa {page}" + (" (OCR)" if block.kind == "ocr" else ""))
        out.append(f"`{block.text}`" if block.kind == "formül" else block.text)
    return "\n".join([*out, *(f"> {w}" for w in warnings)])


def as_json(raw: bytes) -> dict[str, Any]:
    found, warnings = blocks(raw)
    return {"blocks": [asdict(b) for b in found], "warnings": warnings}
