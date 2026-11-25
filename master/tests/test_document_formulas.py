"""Row totals become formulas; unit prices are not summed."""

import openpyxl
import pytest

import document_factory as df
from document_formulas import is_rate_column, row_total_formula

pytestmark = pytest.mark.unit


def test_total_column_detected_only_when_it_is_qty_times_price():
    h = ["Ürün", "Adet", "Birim Fiyat", "Toplam Tutar"]
    assert row_total_formula(h, [["a", 10, 5, 50], ["b", 4, 20, 80]]) == (4, 2, 3)
    assert row_total_formula(h, [["a", 10, 5, 99]]) is None


def test_rate_columns():
    assert is_rate_column("Birim Fiyat (TL)") and not is_rate_column("Toplam Tutar")


def test_xlsx_has_row_formulas_and_no_price_sum(tmp_path):
    content = df._DocContent("T", "s", [], ["Ürün", "Adet", "Birim Fiyat", "Toplam Tutar"], [["kalem", 10, 5, 50], ["defter", 4, 20, 80]], "Türkçe")
    out = df._compile_deliverable_file(tmp_path, "t", "xlsx", content)
    ws = openpyxl.load_workbook(out).worksheets[0]
    assert ws["D5"].value == "=B5*C5" and ws["D6"].value == "=B6*C6"
    assert ws["C7"].value is None and str(ws["D7"].value).startswith("=SUM")
