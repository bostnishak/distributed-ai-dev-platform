"""Word and PDF deliverables carry a readable table and a real chart; numbers are formatted and right aligned."""

import pymupdf
import pytest
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

import document_chart as dc
import document_factory as df

pytestmark = pytest.mark.unit

HEADERS = ["Ay", "Elektronik", "Giyim", "Toplam"]
ROWS = [["Ocak", 12500, 8200, 20700], ["Şubat", 13400, 7900, 21300], ["Mart", 15200, 9100, 24300]]


def _content():
    return df._DocContent("Satış Raporu", "Özet **metin**.", [{"heading": "1. Durum", "content": "- madde"}], HEADERS, ROWS, "Türkçe")


def test_number_formatting_follows_language_and_keeps_ids_raw():
    assert dc.format_cell(12500, "Tutar", "Türkçe") == ("12.500", True)
    assert dc.format_cell(12500, "Amount", "English") == ("12,500", True)
    assert dc.format_cell(2026, "Yıl", "Türkçe") == ("2026", False)
    assert dc.format_cell("Ocak", "Ay", "Türkçe") == ("Ocak", False)


def test_chart_skips_total_columns_and_needs_numbers():
    cats, series = dc.chart_series(HEADERS, ROWS)
    assert cats == ["Ocak", "Şubat", "Mart"] and [n for n, _ in series] == ["Elektronik", "Giyim"]
    assert dc.chart_series(["A", "B"], [["x", "y"], ["z", "w"]]) is None


def test_docx_has_table_with_right_aligned_numbers_and_a_chart_picture(tmp_path):
    out = df._compile_deliverable_file(tmp_path, "t", "docx", _content())
    doc = Document(str(out))
    data_table = doc.tables[-1]
    assert data_table.rows[1].cells[1].text == "12.500"
    assert data_table.rows[1].cells[1].paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.RIGHT
    assert len(doc.inline_shapes) == 1


def test_pdf_has_chart_image_and_formatted_numbers(tmp_path):
    out = df._compile_deliverable_file(tmp_path, "t", "pdf", _content())
    pdf = pymupdf.open(str(out))
    assert any(pg.get_images() for pg in pdf)
    assert "12.500" in "".join(pg.get_text() for pg in pdf)
