"""Ugly real spreadsheets into clean tables: where the header is, merged cells, Turkish and US numbers, dates.

Each column gets one number format, decided from its unambiguous values ("1.250,50" is Turkish, "1,250.50" is US);
a column whose values could be read both ways is left as text and said so. Every row remembers its sheet row.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

_CURRENCY_RE = re.compile(r"\s*(?:TL|TRY|₺|\$|USD|EUR|€|%)\s*", re.IGNORECASE)
_TR_RE = re.compile(r"^-?\d{1,3}(?:\.\d{3})+,\d+$|^-?\d+,\d{1,2}$|^-?\d{1,3}(?:\.\d{3}){2,}$")
_US_RE = re.compile(r"^-?\d{1,3}(?:,\d{3})+\.\d+$|^-?\d+\.\d{1,2}$|^-?\d{1,3}(?:,\d{3}){2,}$")
_INT_RE = re.compile(r"^-?\d+$")
_GROUPED_RE = re.compile(r"^-?\d{1,3}[.,]\d{3}$")  # "1.250" or "1,250": one thousand two hundred fifty, or one and a quarter
_DATE_FORMATS = ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d.%m.%y")
_SCAN_ROWS = 30


@dataclass
class Table:
    sheet: str
    header: list[str]
    rows: list[list[Any]] = field(default_factory=list)
    row_numbers: list[int] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)  # column letters
    types: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def cell(self, row: int, column: int) -> str:
        return f"{self.sheet}!{self.columns[column]}{self.row_numbers[row]}"


def _filled(row: list[Any]) -> int:
    return sum(v not in (None, "") for v in row)


def _header_index(grid: list[list[Any]]) -> int:
    """The first row that names the columns: as wide as the table gets and made of words, not numbers."""
    widest = max((_filled(row) for row in grid[:_SCAN_ROWS]), default=0)
    for index, row in enumerate(grid[:_SCAN_ROWS]):
        words = sum(isinstance(v, str) and bool(re.search(r"[^\W\d]", v)) for v in row)
        if _filled(row) >= max(2, widest - 1) and words >= max(2, _filled(row) - 1):
            return index
    return 0


def _plain(value: Any) -> str:
    return _CURRENCY_RE.sub("", str(value)).replace("\u00a0", "").replace(" ", "")


def _number_style(values: list[str]) -> str:
    turkish, american = sum(bool(_TR_RE.match(v)) for v in values), sum(bool(_US_RE.match(v)) for v in values)
    if turkish and american:
        return "karışık"
    if turkish:
        return "tr"
    if american:
        return "us"
    return "belirsiz" if any(_GROUPED_RE.match(v) for v in values) else "tam"


def _number(text: str, style: str) -> Decimal:
    if style == "tr":
        return Decimal(text.replace(".", "").replace(",", "."))
    return Decimal(text.replace(",", ""))


def _numbers(values: list[Any], assumed: str = "") -> tuple[list[Any], str, str] | None:
    """(converted, type, note) when every filled value of the column is a number written as text or stored as one."""
    texts = [_plain(v) for v in values if isinstance(v, str) and v.strip()]
    if not all(_INT_RE.match(t) or _TR_RE.match(t) or _US_RE.match(t) or _GROUPED_RE.match(t) for t in texts):
        return None
    if not texts and not any(isinstance(v, int | float) for v in values):
        return None
    style = _number_style(texts)
    guessed = style == "belirsiz" and bool(assumed)
    style = assumed if guessed else style
    if style in ("karışık", "belirsiz"):
        note = "Türkçe ve ABD yazımı karışık" if style == "karışık" else "binlik mi ondalık mı belli değil"
        return values, "metin", note
    converted = [None if v in (None, "") else _number(_plain(v), style) if isinstance(v, str) else Decimal(str(v)) for v in values]
    note = {"tr": "Türkçe yazım (1.250,50) çevrildi", "us": "ABD yazımı (1,250.50) çevrildi"}.get(style, "")
    return converted, "sayı", note + (" (aynı tablodaki öbür sütunlara göre varsayıldı)" if guessed else "")


def _dates(values: list[Any]) -> tuple[list[Any], str, str] | None:
    filled = [v for v in values if v not in (None, "")]
    if not filled:
        return None
    if all(isinstance(v, dt.datetime | dt.date) for v in filled):
        return [v.date() if isinstance(v, dt.datetime) else v for v in values], "tarih", ""
    for pattern in _DATE_FORMATS:
        try:
            parsed = [None if v in (None, "") else dt.datetime.strptime(str(v).strip(), pattern).date() for v in values]  # noqa: DTZ007, RUF100  # a calendar date has no time zone
        except ValueError:
            continue
        return parsed, "tarih", f"{pattern.replace('%', '')} biçimindeki tarihler çevrildi"
    return None


def _table_style(table: Table) -> str:
    """The number style the table's unambiguous values prove, "" when they prove none or both."""
    proven = {_number_style([_plain(row[c]) for row in table.rows if isinstance(row[c], str)]) for c in range(len(table.header))} & {"tr", "us"}
    return proven.pop() if len(proven) == 1 else ""


def _typed(table: Table) -> Table:
    assumed = _table_style(table)
    for column, name in enumerate(table.header):
        values = [row[column] for row in table.rows]
        converted, kind, note = _dates(values) or _numbers(values, assumed) or (values, "metin", "")
        for row, value in zip(table.rows, converted, strict=True):
            row[column] = value
        table.types.append(kind)
        if note:
            table.notes.append(f"{name}: {note}")
    return table


def _table(sheet: str, grid: list[list[Any]], offset: int = 1) -> Table | None:
    if not any(_filled(row) for row in grid):
        return None
    start = _header_index(grid)
    used = [i for i in range(len(grid[start])) if any(row[i] not in (None, "") for row in grid[start:] if i < len(row))]
    header = [str(grid[start][i] or f"sütun {get_column_letter(i + 1)}").strip().replace("\n", " ") for i in used]
    table = Table(sheet, header, columns=[get_column_letter(i + 1) for i in used])
    if start:
        table.notes.append(f"başlık {start + offset}. satırda; üstündeki {start} satır açıklama sayıldı")
    for number, row in enumerate(grid[start + 1 :], start + 1 + offset):
        cells = [row[i] if i < len(row) else None for i in used]
        if _filled(cells):
            table.rows.append(cells)
            table.row_numbers.append(number)
    return _typed(table)


def _unmerged(sheet: Any) -> list[list[Any]]:
    grid = [list(row) for row in sheet.iter_rows(values_only=True)]
    for area in sheet.merged_cells.ranges:
        value = grid[area.min_row - 1][area.min_col - 1]
        if area.min_col == area.max_col:  # a label merged downwards belongs to each of its rows; a wide title does not repeat
            for row in range(area.min_row - 1, area.max_row):
                grid[row][area.min_col - 1] = value
    return grid


def from_xlsx(raw: bytes) -> list[Table]:
    book = load_workbook(io.BytesIO(raw), data_only=True)
    try:
        return [table for sheet in book.worksheets if (table := _table(sheet.title, _unmerged(sheet)))]
    finally:
        book.close()


def from_csv(text: str) -> list[Table]:
    first = text.split("\n", 1)[0]
    delimiter = max(("\t", ";", ","), key=first.count) if any(d in text for d in "\t;,") else ","
    delimiter = ";" if text.count(";") >= text.count("\n") and ";" in text else delimiter
    grid = [row for row in csv.reader(io.StringIO(text), delimiter=delimiter)]
    width = max((len(row) for row in grid), default=0)
    table = _table("CSV", [row + [""] * (width - len(row)) for row in grid])
    return [table] if table else []


def _shown(value: Any) -> str:
    if value is None:
        return ""
    return format(value, "f") if isinstance(value, Decimal) else str(value)


def markdown(tables: list[Table], limit: int = 400) -> str:
    """The cleaned tables with their sheet row numbers, and what was assumed about them."""
    parts = []
    for table in tables:
        parts.append(f"### {table.sheet} ({len(table.rows)} satır)")
        parts.append("| satır | " + " | ".join(table.header) + " |\n|" + "---|" * (len(table.header) + 1))
        parts[-1] += "".join(f"\n| {n} | " + " | ".join(_shown(v) for v in row) + " |" for n, row in zip(table.row_numbers[:limit], table.rows[:limit], strict=True))
        sums = [f"{name} toplamı = {format(sum(row[i] for row in table.rows if row[i] is not None), 'f')}" for i, name in enumerate(table.header) if table.types[i] == "sayı"]
        parts += [f"_Not: {note}_" for note in table.notes] + ([f"_Hesaplanan: {'; '.join(sums)}_"] if sums else [])
    return "\n".join(parts)
