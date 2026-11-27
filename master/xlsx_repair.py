"""Make a model-written workbook spec behave like a real spreadsheet, whatever the model got wrong.

* Numbers the model computed by hand (Matrah = Malzeme + İşçilik, KDV = 20% of Matrah ...) become live formulas when the data proves
  the relationship in every row.
* Text cells that are really formulas ("Bütçe - @Toplam") are translated into formulas on the right columns.
* A budget named in the request becomes Toplam / Bütçe / Kalan / Durum rows computed from the sheet's total column.
* Every sheet gets a chart, and several sheets get a comparison sheet when the user asked for one.
"""

from __future__ import annotations

import itertools
import re
from typing import Any

from document_chart import to_number

_BUDGET_RES = (
    re.compile(r"bütçe\w*[^.\d]{0,30}?(\d{1,3}(?:\.\d{3})+|\d+)\s*(?:TL|₺|lira)", re.IGNORECASE),
    re.compile(r"(\d{1,3}(?:\.\d{3})+|\d+)\s*(?:TL|₺|lira)\s*(?:lik\s+|'lik\s+)?bütçe", re.IGNORECASE),
)
_TOTAL_RE = re.compile(r"(toplam\s*tutar|genel\s*toplam|toplam|total)", re.IGNORECASE)
_SAFE_CALL_RE = re.compile(r"\b(?:IF|AND|OR|ROUND|ABS|SUM|AVERAGE|MIN|MAX)\(")
_OPS_RE = re.compile(r"^[\s\d.+\-*/()<>=,\"A-Za-zÇĞİÖŞÜçğıöşü_%$@]*$")


def _column(rows: list[list[Any]], ci: int) -> list[float] | None:
    vals = [to_number(r[ci]) if ci < len(r) else None for r in rows]
    return None if any(v is None for v in vals) else [float(v) for v in vals if v is not None]


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(0.51, 1e-6 * max(abs(a), abs(b)))


def _relation(target: list[float], others: dict[int, list[float]]) -> str | None:
    """A formula over other columns ({i} = column index) reproducing `target` in every row, else None."""
    idx = list(others)
    for a, b in itertools.combinations(idx, 2):
        if all(_close(t, x + y) for t, x, y in zip(target, others[a], others[b], strict=True)):
            return f"{{{a}}}+{{{b}}}"
        if all(_close(t, x * y) for t, x, y in zip(target, others[a], others[b], strict=True)):
            return f"{{{a}}}*{{{b}}}"
    for a, b in itertools.permutations(idx, 2):
        if all(_close(t, x - y) for t, x, y in zip(target, others[a], others[b], strict=True)):
            return f"{{{a}}}-{{{b}}}"
    for a in idx:
        ratios = {round(t / x, 6) for t, x in zip(target, others[a], strict=True) if x}
        if len(ratios) == 1 and (ratio := ratios.pop()) not in (1.0, 0.0) and 0 < ratio < 100:
            return f"{{{a}}}*{ratio:g}"
    for trio in itertools.combinations(idx, 3):
        if all(_close(t, sum(others[i][k] for i in trio)) for k, t in enumerate(target)):
            return "+".join(f"{{{i}}}" for i in trio)
    return None


def recover_numeric(sheet: dict[str, Any]) -> None:
    """Columns that the data proves to be a formula of earlier columns become formulas (left to right, earlier columns first)."""
    rows, headers = sheet["rows"], sheet["headers"]
    cols = {ci: v for ci in range(len(headers)) if (v := _column(rows, ci)) is not None}
    found: dict[int, str] = sheet.setdefault("col_formulas", {})
    for ci in sorted(cols):
        if ci in found or len(rows) < 3:
            continue
        earlier = {k: v for k, v in cols.items() if k < ci and k not in found.values()}
        if len(earlier) >= 1 and (rel := _relation(cols[ci], earlier)):
            found[ci] = rel


def recover_text(sheet: dict[str, Any]) -> None:
    """A column whose cells are all expression text over header names ('Bütçe Limiti - @Toplam Tutar') becomes a formula column."""
    headers, rows = sheet["headers"], sheet["rows"]
    names = sorted(((h, i) for i, h in enumerate(headers)), key=lambda t: -len(t[0]))
    found: dict[int, str] = sheet.setdefault("col_formulas", {})
    for ci in range(len(headers)):
        cells = [str(r[ci]) for r in rows if ci < len(r)]
        if ci in found or not cells or len(set(cells)) != 1 or not (("@" in cells[0]) or any(h in cells[0] for h, _ in names if h != headers[ci])):
            continue
        expr = cells[0]
        for h, i in names:
            expr = re.sub(rf"@?{re.escape(h)}", f"{{{i}}}", expr)
        expr = expr.replace("@", "")
        expr = expr.lstrip("= ")
        if "{" in expr and _OPS_RE.match(expr.replace("{", "").replace("}", "")) and not re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]{3,}\(", _SAFE_CALL_RE.sub("(", expr)):
            found[ci] = expr


def budget_from_request(request: str) -> float | None:
    for rx in _BUDGET_RES:
        if m := rx.search(request or ""):
            return float(m.group(1).replace(".", ""))
    return None


def _total_column(sheet: dict[str, Any]) -> int | None:
    headers = sheet["headers"]
    for ci in range(len(headers) - 1, -1, -1):
        if _TOTAL_RE.search(headers[ci]) and (ci in sheet.get("col_formulas", {}) or _column(sheet["rows"], ci) is not None):
            return ci
    return None


def apply_budget(sheet: dict[str, Any], request: str) -> None:
    """Budget named in the request -> summary rows computed from the total column; per-row budget columns are dropped."""
    budget, total = budget_from_request(request), _total_column(sheet)
    if budget is None or total is None:
        return
    drop = [ci for ci, h in enumerate(sheet["headers"]) if re.search(r"bütçe|kalan|durum", h, re.IGNORECASE) and ci != total]
    keep = [ci for ci in range(len(sheet["headers"])) if ci not in drop]
    remap = {old: new for new, old in enumerate(keep)}
    sheet["headers"] = [sheet["headers"][ci] for ci in keep]
    sheet["rows"] = [[r[ci] if ci < len(r) else "" for ci in keep] for r in sheet["rows"]]
    sheet["col_formulas"] = {remap[ci]: re.sub(r"\{(\d+)\}", lambda m: f"{{{remap.get(int(m.group(1)), int(m.group(1)))}}}", f) for ci, f in sheet.get("col_formulas", {}).items() if ci in remap}
    name = sheet["headers"][remap[total]]
    sheet["summary"] = [
        {"label": "Genel Toplam", "function": "SUM", "column": name}, {"label": "Bütçe", "value": budget},
        {"label": "Kalan Bütçe", "formula": "=@Bütçe-@Genel Toplam"}, {"label": "Durum", "formula": '=IF(@Genel Toplam>@Bütçe,"Bütçe aşıldı","Bütçe içinde")'},
    ]


def _chart_usable(sheet: dict[str, Any]) -> bool:
    """The model's own chart spec only counts when its category and value columns really exist (a wrong name used to mean: no chart at all)."""
    spec = sheet.get("chart")
    headers = sheet["headers"]
    return isinstance(spec, dict) and str(spec.get("category")) in headers and any(v in headers and v != spec.get("category") for v in spec.get("values") or [])


_PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}|^=+\s*\{")


def drop_broken_cells(sheet: dict[str, Any]) -> int:
    """Cells that still hold a template placeholder ('AVERAGE({Sheet}!{Col})', '=={Col}') would show as raw text: they are emptied. Returns how many."""
    n = 0
    for row in sheet["rows"]:
        for i, cell in enumerate(row):
            if isinstance(cell, str) and _PLACEHOLDER_RE.search(cell):
                row[i] = None
                n += 1
    return n


def auto_chart(sheet: dict[str, Any]) -> None:
    """A column chart of the total (or last numeric) column by the first column, unless the model already asked for one."""
    if _chart_usable(sheet) or len(sheet["rows"]) < 3:
        return
    target = _total_column(sheet)
    if target is None:
        numeric = [ci for ci in range(1, len(sheet["headers"])) if _column(sheet["rows"], ci) is not None or ci in sheet.get("col_formulas", {})]
        target = numeric[-1] if numeric else None
    if target is not None and target != 0:
        sheet["chart"] = {"type": "bar", "title": sheet["headers"][target], "category": sheet["headers"][0], "values": [sheet["headers"][target]]}


def _valid_comparison(spec: dict[str, Any]) -> bool:
    cmp = spec.get("comparison")
    column = str(cmp.get("column", "")) if isinstance(cmp, dict) else ""
    return sum(1 for s in spec["sheets"] if column in s["headers"] or any(f["header"] == column for f in s.get("formulas", []))) >= 2


def auto_comparison(spec: dict[str, Any], request: str) -> None:
    """Several sheets with the same total column + a request that says 'karşılaştır' -> a comparison sheet with chart."""
    if _valid_comparison(spec) or len(spec["sheets"]) < 2 or not re.search(r"kar[sş]ıla[sş]t[ıi]r|compar", request or "", re.IGNORECASE):
        return
    cols = [_total_column(s) for s in spec["sheets"]]
    names = {s["headers"][c] for s, c in zip(spec["sheets"], cols, strict=True) if c is not None}
    if len(names) == 1 and all(c is not None for c in cols):
        spec["comparison"] = {"name": "Karşılaştırma", "title": "Şantiye/Birim Karşılaştırması", "column": names.pop(), "function": "SUM", "chart_title": "Toplamların karşılaştırması"}


def _fold(text: str) -> str:
    return text.lower().translate(str.maketrans("çğıöşüâî", "cgiosuai")).replace("i̇", "i")


def fix_names(spec: dict[str, Any], request: str) -> None:
    """Sheet names the model spelled without Turkish letters ('Cankaya') take the spelling the user wrote ('Çankaya')."""
    words = {_fold(w): w for w in re.findall(r"[\wçğıöşüÇĞİÖŞÜ]{3,}", request)}
    for sheet in spec["sheets"]:
        sheet["name"] = words.get(_fold(sheet["name"]), sheet["name"])


def drop_duplicate_formulas(sheet: dict[str, Any]) -> None:
    """A model-written formula column whose header already exists as a data column is a duplicate (the data column is recovered as a formula)."""
    seen = {h.lower() for h in sheet["headers"]}
    sheet["formulas"] = [f for f in sheet.get("formulas", []) if f["header"].lower() not in seen]


_NUMBER_RE = re.compile(r"\d{1,3}(?:\.\d{3})+|\d+")
_SAMPLE_RE = re.compile(r"örnek|deneme|temsili|rastgele|sample|example|dummy", re.IGNORECASE)
_TOTAL_ASKED_RE = re.compile(r"toplam|formül|total|\bsum\b", re.IGNORECASE)


def _given_numbers(request: str) -> set[float]:
    return {n for n in (float(m.replace(".", "")) for m in _NUMBER_RE.findall(request or "")) if n >= 100}


def keep_given_data(spec: dict[str, Any], request: str) -> int:
    """When the user wrote the figures, rows made only of other figures are the model's inventions: they are removed.

    A row stays when at least one of its numbers is the user's (derived columns are fine) or it has no numbers; a sheet
    that loses every row is removed. Requests that ask for sample data, or give fewer than two figures, are left alone.
    """
    given = _given_numbers(request)
    if len(given) < 2 or _SAMPLE_RE.search(request):
        return 0
    removed = 0
    for sheet in spec["sheets"]:
        kept = []
        for row in sheet["rows"]:
            numbers = {n for n in (to_number(c) for c in row) if n}
            if numbers and not numbers & given:
                removed += 1
            else:
                kept.append(row)
        sheet["rows"] = kept
    if any(s["rows"] for s in spec["sheets"]):
        spec["sheets"] = [s for s in spec["sheets"] if s["rows"]]
    return removed


def drop_invented_parts(spec: dict[str, Any], request: str) -> None:
    """With the user's own figures: columns the model added but left empty or zero, and fixed numbers it made up for the summary, go."""
    given = _given_numbers(request)
    if len(given) < 2 or _SAMPLE_RE.search(request):
        return
    for sheet in spec["sheets"]:
        def blank(cell: Any) -> bool:
            return cell in (None, "", 0, "0") or (isinstance(cell, str) and bool(_PLACEHOLDER_RE.search(cell)))

        keep = [ci for ci in range(len(sheet["headers"])) if ci == 0 or not all(blank(r[ci] if ci < len(r) else None) for r in sheet["rows"])]
        if len(keep) >= 2 and len(keep) < len(sheet["headers"]):
            sheet["headers"] = [sheet["headers"][ci] for ci in keep]
            sheet["rows"] = [[r[ci] if ci < len(r) else "" for ci in keep] for r in sheet["rows"]]
        sheet["summary"] = [s for s in sheet.get("summary") or [] if not (isinstance(s, dict) and isinstance(s.get("value"), int | float) and float(s["value"]) not in given)]


def _has_total(sheet: dict[str, Any]) -> bool:
    live = any(isinstance(s, dict) and str(s.get("function", "")).upper() == "SUM" and s.get("column") in sheet["headers"] for s in sheet.get("summary") or [])
    return live or bool(sheet.get("formulas") or sheet.get("col_formulas"))


def ensure_totals(spec: dict[str, Any], request: str) -> None:
    """A total or a formula was asked for and a sheet has neither: add column totals (and their sum) as live formulas."""
    if not _TOTAL_ASKED_RE.search(request or ""):
        return
    for sheet in spec["sheets"]:
        if _has_total(sheet) or not sheet["rows"]:
            continue
        numeric = [h for ci, h in enumerate(sheet["headers"]) if ci and _column(sheet["rows"], ci) is not None]
        if not numeric:
            continue
        totals = [{"label": f"Toplam {h}", "function": "SUM", "column": h} for h in numeric[:6]]
        if len(numeric) > 1:
            totals.append({"label": "Genel Toplam", "formula": "=" + "+".join(f"@Toplam {h}" for h in numeric[:6])})
        sheet["summary"] = totals + list(sheet.get("summary") or [])


def repair(spec: dict[str, Any], request: str) -> dict[str, Any]:
    fix_names(spec, request)
    keep_given_data(spec, request)
    drop_invented_parts(spec, request)
    for sheet in spec["sheets"]:
        drop_duplicate_formulas(sheet)
        recover_text(sheet)
        recover_numeric(sheet)
        apply_budget(sheet, request)
        drop_broken_cells(sheet)
        auto_chart(sheet)
    ensure_totals(spec, request)
    auto_comparison(spec, request)
    return spec
