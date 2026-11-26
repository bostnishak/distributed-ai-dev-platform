"""Model-designed workbooks: validation of the spec and what ends up in the file."""

from __future__ import annotations

import pytest
from openpyxl import load_workbook

import xlsx_builder as xb

pytestmark = pytest.mark.unit

SHEET = {
    "name": "Bütçe", "headers": ["Kalem", "Adet", "Fiyat (TL)"],
    "rows": [["Market", 4, 1200], ["Kira", 1, 15000], ["Fatura", 3, 650]],
    "formula_columns": [{"header": "Toplam (TL)", "formula": "={Adet}*{Fiyat (TL)}"}, {"header": "Kötü", "formula": "=SYSTEM(A1)"}, {"header": "Dış", "formula": "=cmd|'/c calc'!A0"}],
    "summary": [{"label": "Toplam", "function": "SUM", "column": "Toplam (TL)"}, {"label": "x", "function": "EXEC", "column": "Kalem"}],
    "chart": {"type": "pie", "title": "Dağılım", "category": "Kalem", "values": ["Toplam (TL)"]},
}


def test_unsafe_formulas_are_dropped():
    spec = xb.parse_spec({"title": "T", "sheets": [SHEET]})
    assert [f["header"] for f in spec["sheets"][0]["formulas"]] == ["Toplam (TL)"]


def test_unusable_specs_are_rejected():
    assert xb.parse_spec(None) is None
    assert xb.parse_spec({"sheets": [{"headers": ["a"], "rows": [[1]]}]}) is None
    assert xb.parse_spec({"sheets": "x"}) is None


def test_workbook_has_row_formulas_summary_and_chart(tmp_path):
    out = tmp_path / "w.xlsx"
    xb.build_workbook(out, xb.parse_spec({"title": "Aylık Bütçe", "description": "Takip", "sheets": [SHEET]}))
    ws = load_workbook(out)["Bütçe"]
    assert ws["A1"].value == "Aylık Bütçe" and ws["D5"].value == "=B5*C5"
    assert ws["D8"].value == "=SUM(D5:D7)" and ws["A8"].value == "Toplam"
    assert len(ws._charts) == 1


def test_numbers_are_numbers_and_sheet_name_is_safe():
    assert xb._value("12.5") == (12.5, "#,##0.00")
    spec = xb.parse_spec({"sheets": [{**SHEET, "name": "a/b:c*"}]})
    assert all(ch not in spec["sheets"][0]["name"] for ch in "/:*")


def test_budget_rows_and_comparison_sheet(tmp_path):
    sheet = {"headers": ["Ay", "Gider (TL)"], "rows": [["Ocak", 100], ["Şubat", 200], ["Mart", 300]],
             "summary": [{"label": "Toplam", "function": "SUM", "column": "Gider (TL)"}, {"label": "Bütçe", "value": 500},
                         {"label": "Kalan", "formula": "=@Bütçe-@Toplam"}, {"label": "Durum", "formula": "=IF(@Toplam>@Bütçe,\"Aşıldı\",\"İçinde\")"}]}
    spec = xb.parse_spec({"title": "T", "sheets": [{**sheet, "name": "A"}, {**sheet, "name": "B"}], "comparison": {"column": "Gider (TL)", "function": "SUM"}})
    out = tmp_path / "c.xlsx"
    xb.build_workbook(out, spec)
    wb = load_workbook(out)
    ws = wb["A"]
    assert ws["B9"].value == 500 and ws["B10"].value == "=B9-B8"
    assert "IF(B8>B9" in str(ws["B11"].value)
    assert wb["Karşılaştırma"]["B5"].value == "=SUM('A'!B5:B7)"


def test_unsafe_cell_text_is_never_a_formula(tmp_path):
    sheet = {**SHEET, "rows": [["=HYPERLINK(\"http://x\",\"a\")", 1, 2], ["=SUM(B5:B6)", 1, 2], ["-5", 1, 2]]}
    out = tmp_path / "u.xlsx"
    xb.build_workbook(out, xb.parse_spec({"title": "T", "sheets": [sheet]}))
    ws = load_workbook(out)["Bütçe"]
    assert not str(ws["A5"].value).startswith("=") and ws["A6"].value == "=SUM(B5:B6)" and ws["A7"].value == -5


def test_header_name_references_become_the_right_columns():
    sheet = {"name": "S", "headers": ["Ay", "Malzeme", "İşçilik"], "rows": [["Ocak", 10, 5], ["Şubat", 20, 6]],
             "formula_columns": [{"header": "Matrah", "formula": "={Malzeme}+{İşçilik}"}, {"header": "KDV", "formula": "={Matrah}*0.2"}, {"header": "Kötü", "formula": "={Yok}+1"}]}
    s = xb.parse_spec({"title": "T", "sheets": [sheet]})["sheets"][0]
    assert [(f["header"], f["formula"]) for f in s["formulas"]] == [("Matrah", "=B{r}+C{r}"), ("KDV", "=D{r}*0.2")]


def test_letter_references_to_text_columns_are_rejected():
    sheet = {"name": "S", "headers": ["Ay", "Malzeme", "İşçilik"], "rows": [["Ocak", 10, 5], ["Şubat", 20, 6]],
             "formula_columns": [{"header": "Yanlış", "formula": "=A{r}+B{r}"}, {"header": "Doğru", "formula": "=B{r}+C{r}"}]}
    s = xb.parse_spec({"title": "T", "sheets": [sheet]})["sheets"][0]
    assert [f["header"] for f in s["formulas"]] == ["Doğru"]


def test_cross_sheet_references_need_real_cells():
    assert xb._safe_formula("=SUM('A'!B5:B9)") and not xb._safe_formula("=AVERAGE(Kadıköy!Matrah (TL))")


def test_placeholder_cells_are_emptied_and_an_unusable_chart_spec_is_replaced():
    import xlsx_repair

    sheet = {"headers": ["Ad", "Not", "Ort"], "rows": [["A", 80, "AVERAGE({X}!{Not})"], ["B", 90, "=={Not}"], ["C", 70, None]], "chart": {"type": "bar", "category": "Yok", "values": ["Hiç"]}, "formulas": [], "col_formulas": {}}
    assert xlsx_repair.drop_broken_cells(sheet) == 2
    xlsx_repair.auto_chart(sheet)
    assert sheet["chart"]["category"] == "Ad" and sheet["chart"]["values"] == ["Not"]
