"""Deterministic quality scores and the feedback text that drives the retry."""

from __future__ import annotations

import pytest

import deliverable_score as ds

pytestmark = pytest.mark.unit

BLANK = "[................]"


def _doc(*blocks):
    return {"title": "T", "subtitle": "", "blocks": list(blocks)}


def test_blank_numbers_and_leftover_placeholders_lower_the_score():
    good = _doc({"type": "para", "text": "Aylık gelir 306.000 TL."}, {"type": "table", "headers": ["a", "b"], "rows": [["x", "1"]], "caption": ""},
                {"type": "para", "text": "Sonuç metni yeterince uzun bir cümledir."}, {"type": "bullets", "items": ["a", "b"]})
    bad = _doc({"type": "para", "text": f"Aylık gelir {BLANK} TL ve {BLANK} adet {{x}}."}, {"type": "para", "text": "Metin."}, {"type": "bullets", "items": ["a"]}, {"type": "para", "text": "b"})
    assert ds.score_document(good, "iş planı hesabı", 0)[0] >= 90
    score, issues = ds.score_document(bad, "iş planı hesabı", 0)
    assert score < 70 and any("boş bırakılmış" in i for i in issues) and any("yer tutucu" in i for i in issues)


def test_identity_blanks_are_fine_in_contracts():
    spec = _doc({"type": "para", "text": f"T.C. Kimlik No: {BLANK}, Adres: {BLANK}"}, {"type": "para", "text": "Madde 1 - metin yeterince uzun."}, {"type": "bullets", "items": ["a"]}, {"type": "para", "text": "b"})
    assert ds.score_document(spec, "sözleşme", 0)[0] >= 90


def test_page_overflow_is_penalised():
    spec = _doc({"type": "para", "text": "x " * 400}, {"type": "para", "text": "y " * 300}, {"type": "bullets", "items": ["a"]}, {"type": "table", "headers": ["a", "b"], "rows": [["1", "2"]], "caption": ""})
    assert ds.score_document(spec, "2 sayfa", 2, 3)[0] < ds.score_document(spec, "2 sayfa", 2, 2)[0]


def test_workbook_without_formulas_or_chart_scores_low():
    sheet = {"headers": ["Ay", "Tutar"], "rows": [["a", 1]] * 6, "formulas": [], "summary": [], "chart": None}
    score, issues = ds.score_workbook({"sheets": [sheet], "comparison": None}, "bütçe takibi")
    assert score <= 50 and any("formül" in i for i in issues) and any("bütçe" in i for i in issues)
    good = {**sheet, "col_formulas": {1: "{0}"}, "chart": {"type": "bar"}, "summary": [{"label": "T"}]}
    assert ds.score_workbook({"sheets": [good], "comparison": None}, "bütçe takibi")[0] >= 85


def test_feedback_lists_every_problem():
    text = ds.feedback(["a sorunu", "b sorunu"])
    assert "- a sorunu" in text and "- b sorunu" in text and text.startswith("\n\n[")
