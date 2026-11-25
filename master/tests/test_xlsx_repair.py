"""A messy model-written workbook is turned into a live spreadsheet."""

from __future__ import annotations

import pytest
from openpyxl import load_workbook

import xlsx_builder as xb
import xlsx_repair as xr

pytestmark = pytest.mark.unit

HEAD = ["Ay", "Malzeme (TL)", "İşçilik (TL)", "Matrah (TL)", "KDV (TL)", "Toplam Tutar (TL)", "Bütçe (TL)", "Durum"]


def _rows(base):
    return [[m, b, b - 40000, 2 * b - 40000, (2 * b - 40000) * 0.2, (2 * b - 40000) * 1.2, 2000000, 'IF(@Toplam Tutar (TL)>@Bütçe (TL),"Aşıldı","İçinde")'] for m, b in zip(["Oca", "Şub", "Mar", "Nis"], base, strict=True)]


def _spec(request="3 şantiye, bütçe 2.000.000 TL ise aşıldı mı, şantiyelere göre karşılaştırma olsun"):
    raw = {"title": "T", "sheets": [{"name": "A", "headers": HEAD, "rows": _rows([450000, 480000, 460000, 455000])}, {"name": "B", "headers": HEAD, "rows": _rows([510000, 530000, 520000, 515000])}]}
    return xb.parse_spec(raw, request)


def test_hand_computed_columns_become_formulas():
    s = _spec()["sheets"][0]
    assert s["col_formulas"][3] == "{1}+{2}" and s["col_formulas"][4] == "{3}*0.2" and s["col_formulas"][5] == "{3}+{4}"


def test_budget_in_the_request_becomes_summary_rows_and_row_budget_columns_go():
    s = _spec()["sheets"][0]
    assert "Bütçe (TL)" not in s["headers"] and "Durum" not in s["headers"]
    assert [r.get("label") for r in s["summary"]] == ["Genel Toplam", "Bütçe", "Kalan Bütçe", "Durum"] and s["summary"][1]["value"] == 2000000


def test_chart_and_comparison_are_added():
    spec = _spec()
    assert spec["sheets"][0]["chart"]["values"] == ["Toplam Tutar (TL)"]
    assert spec["comparison"]["column"] == "Toplam Tutar (TL)"
    assert _spec("sadece tablo olsun")["comparison"] is None


def test_workbook_has_live_formulas(tmp_path):
    out = tmp_path / "w.xlsx"
    xb.build_workbook(out, _spec())
    ws = load_workbook(out)["A"]
    assert ws["D5"].value == "=B5+C5" and ws["E5"].value == "=D5*0.2" and ws["F5"].value == "=D5+E5"
    assert ws["F9"].value == "=SUM(F5:F8)" and ws["F10"].value == 2000000 and ws["F11"].value == "=F10-F9"


def test_budget_amount_is_read_from_the_request():
    assert xr.budget_from_request("bütçe 2.000.000 TL ise") == 2000000.0
    assert xr.budget_from_request("500 TL bütçem var") == 500.0
    assert xr.budget_from_request("bütçe yok") is None


def test_duplicate_formula_columns_and_ascii_sheet_names_are_fixed():
    raw = {"title": "T", "sheets": [
        {"name": "Cankaya", "headers": ["Ay", "A", "B", "Toplam Tutar"], "rows": [["O", 1, 2, 3], ["Ş", 2, 3, 5], ["M", 4, 4, 8]], "formula_columns": [{"header": "Toplam Tutar", "formula": "={A}+{B}"}]},
        {"name": "Bornova", "headers": ["Ay", "A", "B", "Toplam Tutar"], "rows": [["O", 1, 2, 3], ["Ş", 2, 3, 5], ["M", 4, 4, 8]]}]}
    spec = xb.parse_spec(raw, "Çankaya ve Bornova şantiyeleri için karşılaştırma olsun")
    assert spec["sheets"][0]["name"] == "Çankaya" and spec["sheets"][0]["formulas"] == []
    assert spec["comparison"]["column"] == "Toplam Tutar"
