"""Build a real, request-specific workbook from a model-written spec: sheets, per-row formulas, summary rows and a chart.

The spec is validated before anything is drawn (formulas only use whitelisted functions and cell references), so a
model slip becomes a plain value instead of a broken or unsafe cell.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import xlsx_repair

_FUNCS = {"SUM", "AVERAGE", "MIN", "MAX", "COUNT", "IF", "ROUND", "ABS", "AND", "OR"}
_SUMMARY_FUNCS = {"SUM", "AVERAGE", "MIN", "MAX", "COUNT"}
_FORMULA_RE = re.compile(r"^=[\w+\-*/().,:<>=&\"' {}%$!]*$")  # "!" only for sheet references: no [external], no | (DDE), no HYPERLINK-style functions
_CHARTS = {"bar": BarChart, "line": LineChart, "pie": PieChart}
_THIN = Side(style="thin", color="CBD5E1")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_MAX_ROWS, _MAX_SHEETS = 60, 4


_SHEET_REF_OK = re.compile(r"!\$?[A-Z]{1,3}\$?\d")


def _safe_formula(formula: str) -> bool:
    if not isinstance(formula, str) or not _FORMULA_RE.match(formula) or "[" in formula:
        return False
    if any(not _SHEET_REF_OK.match(formula[i:]) for i, ch in enumerate(formula) if ch == "!"):
        return False  # a sheet reference must be followed by a real cell reference, not a header name
    return all(name.upper() in _FUNCS for name in re.findall(r"([A-Za-z_]+)\(", formula))


def _by_header(formula: str, names: list[str]) -> str | None:
    """Turn {Header Name} references into column letters with the row placeholder ({r}); None when a name is unknown."""
    missing = False

    def sub(m: re.Match[str]) -> str:
        nonlocal missing
        key = m.group(1).strip()
        if key == "r":
            return m.group(0)
        if key not in names:
            missing = True
            return ""
        return f"{get_column_letter(names.index(key) + 1)}{{r}}"

    out = re.sub(r"\{([^{}]+)\}", sub, formula)
    return None if missing else out


def _numeric_refs_only(formula: str, names: list[str], first_row: list[Any], n_data: int) -> bool:
    """Letter references such as B{r} must point at columns that hold numbers (or earlier formula columns), never at text."""
    for letter in re.findall(r"\b([A-Z]{1,2})\{r\}", formula):
        idx = sum((ord(c) - 64) * 26**i for i, c in enumerate(reversed(letter))) - 1
        if idx >= len(names) or (idx < n_data and _value(first_row[idx])[1] is None):
            return False
    return True


def _formula_columns(raw: dict[str, Any], headers: list[str], rows: list[list[Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    names = list(headers)
    for f in raw.get("formula_columns") or []:
        if not isinstance(f, dict) or not f.get("header"):
            continue
        formula = _by_header(str(f.get("formula", "")), names)
        if formula and _safe_formula(formula) and _numeric_refs_only(formula, names, rows[0], len(headers)):
            out.append({"header": str(f["header"]), "formula": formula})
            names.append(str(f["header"]))
    return out[:3]


def _clean_sheet(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    headers = [str(h).strip() for h in raw.get("headers") or [] if str(h).strip()]
    rows = [r for r in (raw.get("rows") or []) if isinstance(r, list) and r][:_MAX_ROWS]
    if len(headers) < 2 or len(rows) < 2:
        return None
    rows = [(list(r) + [""] * len(headers))[: len(headers)] for r in rows]
    name = re.sub(r"[\/*?:\[\]]", " ", str(raw.get("name") or "Sayfa")).strip()[:28] or "Sayfa"
    return {"name": name, "headers": headers, "rows": rows, "formulas": _formula_columns(raw, headers, rows), "summary": raw.get("summary") or [], "chart": raw.get("chart")}


def parse_spec(raw: dict[str, Any] | None, request: str = "") -> dict[str, Any] | None:
    """Normalised spec, or None when the model's JSON does not describe a usable workbook."""
    if not isinstance(raw, dict) or not isinstance(raw.get("sheets"), list):
        return None
    sheets = [s for s in (_clean_sheet(x) for x in raw["sheets"][:_MAX_SHEETS]) if s]
    if not sheets:
        return None
    spec = {"title": str(raw.get("title") or "").strip()[:90], "description": str(raw.get("description") or "").strip()[:400], "sheets": sheets, "comparison": raw.get("comparison")}
    return xlsx_repair.repair(spec, request)


def _value(cell: Any) -> tuple[Any, str | None]:
    if isinstance(cell, bool) or cell is None:
        return ("" if cell is None else str(cell)), None
    if isinstance(cell, int):
        return cell, "#,##0"
    if isinstance(cell, float):
        return cell, "#,##0.00"
    text = re.sub(r"^=+", "=", str(cell).strip())  # "==B5-C5" is a typing slip, not text
    if text.startswith(("=", "+", "-", "@")) and not re.fullmatch(r"-?\d+(?:\.\d+)?", text) and not (text.startswith("=") and _safe_formula(text)):
        text = text.lstrip("=+-@ ")  # a cell that is not a whitelisted formula must never be executed by Excel
    num = re.fullmatch(r"-?\d+(?:\.\d+)?", text)
    if num:
        return (float(text), "#,##0.00") if "." in text else (int(text), "#,##0")
    return text, None


def _write_header(ws: Any, title: str, description: str, width: int) -> None:
    last = get_column_letter(max(3, width))
    ws.merge_cells(f"A1:{last}1")
    ws["A1"].value, ws["A1"].fill = title, PatternFill("solid", fgColor="1E293B")
    ws["A1"].font, ws["A1"].alignment = Font(name="Calibri", size=14, bold=True, color="FFFFFF"), Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 30
    if description:
        ws.merge_cells(f"A2:{last}2")
        ws["A2"].value, ws["A2"].font = description, Font(name="Calibri", size=10, italic=True, color="334155")
        ws["A2"].alignment = Alignment(vertical="center", wrap_text=True)
        ws.row_dimensions[2].height = max(24.0, min(64.0, (len(description) // 80 + 1) * 15.0))


def _row_formula(template: str, row: int) -> str:
    """'{1}+{2}' (column indexes) -> '=B5+C5' for sheet row 5; '' when the result would not be a whitelisted formula."""
    formula = "=" + re.sub(r"\{(\d+)\}", lambda m: f"{get_column_letter(int(m.group(1)) + 1)}{row}", template)
    return formula if _safe_formula(formula) else ""


def _write_table(ws: Any, sheet: dict[str, Any]) -> tuple[list[str], int]:
    headers = sheet["headers"] + [f["header"] for f in sheet["formulas"]]
    for ci, h in enumerate(headers, 1):
        c = ws.cell(4, ci, h)
        c.font, c.border = Font(name="Calibri", bold=True, color="FFFFFF", size=11), _BORDER
        c.fill, c.alignment = PatternFill("solid", fgColor="4F46E5"), Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[4].height = 28
    widths = [max(12, min(34, len(h) + 4)) for h in headers]
    recovered = sheet.get("col_formulas", {})
    for ri, row in enumerate(sheet["rows"], 5):
        base = [(_row_formula(recovered[ci], ri), "#,##0.00") if ci in recovered and _row_formula(recovered[ci], ri) else _value(v) for ci, v in enumerate(row)]
        cells: list[tuple[Any, str | None]] = base + [(f["formula"].replace("{r}", str(ri)), "#,##0.00") for f in sheet["formulas"]]
        for ci, (val, fmt) in enumerate(cells, 1):
            c = ws.cell(ri, ci, val)
            c.border, c.font = _BORDER, Font(name="Calibri", size=10)
            c.alignment = Alignment(vertical="center", horizontal="right" if fmt else "left", wrap_text=True)
            if fmt:
                c.number_format = fmt
            if ri % 2 == 0:
                c.fill = PatternFill("solid", fgColor="F8FAFC")
            widths[ci - 1] = min(46, max(widths[ci - 1], len(str(val)) + 3))
    for ci, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(ci)].width = w
    return headers, 4 + len(sheet["rows"])


def _summary_cell(headers: list[str], last: int, item: dict[str, Any], refs: dict[str, str]) -> tuple[int, Any] | None:
    """(column index, value) for one summary row: an aggregate over a column, a fixed number, or a formula over other summary rows (@Label)."""
    func, col = str(item.get("function", "")).upper(), str(item.get("column", ""))
    if func in _SUMMARY_FUNCS and col in headers:
        ci = headers.index(col) + 1
        letter = get_column_letter(ci)
        return ci, f"={func}({letter}5:{letter}{last})"
    ci = int(refs.get("__col__", len(headers)))
    if isinstance(item.get("value"), (int, float)) and not isinstance(item.get("value"), bool):
        return ci, item["value"]
    formula = str(item.get("formula", ""))
    for label in sorted((k for k in refs if k != "__col__"), key=len, reverse=True):
        formula = formula.replace(f"@{label}", refs[label])
    return (ci, formula) if "@" not in formula and _safe_formula(formula) else None


def _write_summary(ws: Any, sheet: dict[str, Any], headers: list[str], last: int) -> int:
    row, refs = last + 1, {}
    for item in [s for s in sheet["summary"] if isinstance(s, dict)][:8]:
        cell = _summary_cell(headers, last, item, refs)
        if cell is None:
            continue
        ci, value = cell
        refs.setdefault("__col__", str(ci))
        label = str(item.get("label") or item.get("function") or "")
        refs[label] = f"{get_column_letter(ci)}{row}"
        ws.cell(row, 1, label).font = Font(name="Calibri", bold=True, color="1E293B")
        c = ws.cell(row, ci, value)
        c.font, c.number_format = Font(name="Calibri", bold=True, color="1E293B"), "#,##0.00" if not isinstance(value, str) or value.startswith("=") else "General"
        for k in range(1, len(headers) + 1):
            ws.cell(row, k).fill, ws.cell(row, k).border = PatternFill("solid", fgColor="E2E8F0"), _BORDER
        row += 1
    return row


def _add_comparison(wb: Any, spec: dict[str, Any]) -> None:
    """A sheet that compares the data sheets on one metric (e.g. total cost per site) with a chart."""
    cmp = spec.get("comparison")
    if not isinstance(cmp, dict):
        return
    metric, func = str(cmp.get("column", "")), str(cmp.get("function", "SUM")).upper()
    parts = [s for s in spec["sheets"] if metric in s["headers"] + [f["header"] for f in s["formulas"]]]
    if len(parts) < 2 or func not in _SUMMARY_FUNCS:
        return
    ws: Any = wb.create_sheet(str(cmp.get("name") or "Karşılaştırma")[:28])
    _write_header(ws, str(cmp.get("title") or ws.title), "", 3)
    for ci, h in enumerate(("", metric), 1):
        ws.cell(4, ci, h or " ").font = Font(name="Calibri", bold=True, color="FFFFFF")
        ws.cell(4, ci).fill = PatternFill("solid", fgColor="4F46E5")
    for ri, sh in enumerate(parts, 5):
        letter = get_column_letter((sh["headers"] + [f["header"] for f in sh["formulas"]]).index(metric) + 1)
        ws.cell(ri, 1, sh["name"]).border = _BORDER
        c = ws.cell(ri, 2, f"={func}('{sh['name']}'!{letter}5:{letter}{4 + len(sh['rows'])})")
        c.number_format, c.border = "#,##0.00", _BORDER
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 26, max(16, len(metric) + 4)
    chart = BarChart()
    chart.title, chart.width, chart.height = str(cmp.get("chart_title") or metric)[:80], 16, 8
    chart.add_data(Reference(ws, min_col=2, min_row=4, max_row=4 + len(parts)), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=1, min_row=5, max_row=4 + len(parts)))
    chart.x_axis.delete = chart.y_axis.delete = False
    ws.add_chart(chart, f"A{len(parts) + 7}")


def _add_chart(ws: Any, sheet: dict[str, Any], headers: list[str], last: int, anchor_row: int) -> None:
    spec = sheet["chart"]
    if not isinstance(spec, dict) or str(spec.get("category")) not in headers or last < 6:
        return
    values = [v for v in (spec.get("values") or []) if v in headers and v != spec["category"]][:3]
    if not values:
        return
    chart = _CHARTS.get(str(spec.get("type", "bar")).lower(), BarChart)()
    chart.title, chart.width, chart.height = str(spec.get("title") or "")[:80], 18, 9
    for name in values if not isinstance(chart, PieChart) else values[:1]:
        chart.add_data(Reference(ws, min_col=headers.index(name) + 1, min_row=4, max_row=last), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=headers.index(str(spec["category"])) + 1, min_row=5, max_row=last))
    if not isinstance(chart, PieChart):
        chart.x_axis.delete = chart.y_axis.delete = False  # openpyxl hides the axes in current Excel unless told otherwise
        chart.x_axis.title, chart.y_axis.title = str(spec["category"]), values[0] if len(values) == 1 else None
    ws.add_chart(chart, f"A{anchor_row + 2}")


def build_workbook(out_path: Path, spec: dict[str, Any]) -> None:
    wb = Workbook()
    for idx, sheet in enumerate(spec["sheets"]):
        ws: Any = wb.active if idx == 0 else wb.create_sheet()
        ws.title = sheet["name"]
        _write_header(ws, spec["title"] if idx == 0 else sheet["name"], spec["description"] if idx == 0 else "", len(sheet["headers"]) + len(sheet["formulas"]))
        headers, last = _write_table(ws, sheet)
        ws.auto_filter.ref = f"A4:{get_column_letter(len(headers))}{last}"
        ws.freeze_panes = "A5"
        if (num := [i for i, v in enumerate(sheet["rows"][0], 1) if _value(v)[1]]) and len(sheet["rows"]) >= 3:
            letter = get_column_letter(num[-1])
            ws.conditional_formatting.add(f"{letter}5:{letter}{last}", ColorScaleRule(start_type="min", start_color="F8FAFC", end_type="max", end_color="A5B4FC"))
        end = _write_summary(ws, sheet, headers, last)
        _add_chart(ws, sheet, headers, last, end)
    _add_comparison(wb, spec)
    wb.save(str(out_path))
