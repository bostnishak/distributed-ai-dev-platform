"""What a workbook can get wrong without showing an error cell: formulas that refer back to themselves, and columns
too narrow to show what is in them."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter

_REF_RE = re.compile(r"(?:(?:'(?P<quoted>[^']+)'|(?P<sheet>[A-Za-zÇĞİÖŞÜçğıöşü_][\w]*))!)?\$?(?P<col>[A-Z]{1,3})\$?(?P<row>\d+)(?::\$?(?P<col2>[A-Z]{1,3})\$?(?P<row2>\d+))?")
_STRING_RE = re.compile(r'"[^"]*"')
_MAX_RANGE = 5000
_DEFAULT_WIDTH = 8.43

Cell = tuple[str, int, int]  # sheet title, row, column


def _references(formula: str, sheet: str) -> Iterator[Cell]:
    for match in _REF_RE.finditer(_STRING_RE.sub('""', formula)):
        target = match["quoted"] or match["sheet"] or sheet
        first, last = column_index_from_string(match["col"]), column_index_from_string(match["col2"] or match["col"])
        top, bottom = int(match["row"]), int(match["row2"] or match["row"])
        if (last - first + 1) * (bottom - top + 1) > _MAX_RANGE:
            continue
        yield from ((target, r, c) for r in range(top, bottom + 1) for c in range(first, last + 1))


def _cycle(graph: dict[Cell, list[Cell]]) -> list[Cell]:
    """One loop of formulas, in order; [] when there is none. Iterative, so long chains cannot overflow the stack."""
    done: set[Cell] = set()
    for start in graph:
        if start in done:
            continue
        path, on_path, stack = [start], {start}, [iter(graph[start])]
        while stack:
            following = next((n for n in stack[-1] if n in graph and n not in done), None)
            if following is None:
                done.add(path[-1])
                on_path.discard(path.pop())
                stack.pop()
            elif following in on_path:
                return path[path.index(following) :]
            else:
                path.append(following)
                on_path.add(following)
                stack.append(iter(graph[following]))
    return []


def circular_references(book: Any) -> list[str]:
    graph = {(ws.title, cell.row, cell.column): list(_references(cell.value, ws.title))
             for ws in book for row in ws.iter_rows() for cell in row if isinstance(cell.value, str) and cell.value.startswith("=")}
    loop = _cycle(graph)
    if not loop:
        return []
    names = [f"{sheet}!{get_column_letter(col)}{row}" for sheet, row, col in loop[:6]]
    return ["döngüsel başvuru: " + " → ".join([*names, names[0]])]


def clipped_cells(book: Any) -> list[str]:
    """Cells whose content does not fit: a number shows as ####, a text is cut off by the filled cell on its right."""
    found = []
    for ws in book:
        merged = {(r, c) for area in ws.merged_cells.ranges for r in range(area.min_row, area.max_row + 1) for c in range(area.min_col, area.max_col + 1)}
        for row in ws.iter_rows():
            for cell in row:
                value = cell.value
                if value is None or (cell.row, cell.column) in merged or (cell.alignment and cell.alignment.wrap_text):
                    continue
                width = ws.column_dimensions[get_column_letter(cell.column)].width or _DEFAULT_WIDTH
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    needed, kind = len(f"{value:,.2f}" if "0.00" in cell.number_format else f"{value:,.0f}"), "sayı #### görünür"
                elif isinstance(value, str) and not value.startswith("=") and ws.cell(cell.row, cell.column + 1).value is not None:
                    needed, kind = len(value), "metin kesilir"
                else:
                    continue
                if needed > width + 1:
                    found.append(f"{ws.title}!{cell.coordinate}: sütun dar, {kind}")
    return found[:4]


def problems(path: Path) -> list[str]:
    book = load_workbook(path)
    try:
        return circular_references(book) + clipped_cells(book)
    finally:
        book.close()
