"""Deck builder: outline acceptance, slide-count parsing, layouts render without errors and every layout fills its slide."""

from __future__ import annotations

from pathlib import Path

import pytest
from pptx import Presentation

import deep_research as dr

pytestmark = pytest.mark.unit

SLIDES = [
    {"title": "Neden önemli", "layout": "bullets", "bullets": ["Birinci madde", "İkinci madde", "Üçüncü madde"], "key_fact": "Kısa çıkarım.", "notes": "Not."},
    {"title": "Satış hedefi", "layout": "chart", "chart": {"title": "Satış", "labels": ["2026", "2027", "2028"], "values": [12000, 30000, 65000], "unit": "adet"}, "bullets": ["a", "b"], "key_fact": "Büyüme."},
    {"title": "İki yön", "layout": "two_column", "columns": {"left_title": "Sol", "left_bullets": ["x1", "x2", "x3"], "right_title": "Sağ", "right_bullets": ["y1", "y2", "y3"]}, "key_fact": "Fark."},
    {"title": "Süreç adımları", "layout": "steps", "bullets": ["Fark et: ilk adım", "Durdur: ikinci adım", "Bildir: üçüncü adım"], "key_fact": "Hız önemli."},
    {"title": "Karşılaştırma", "layout": "table", "table": {"headers": ["A", "B", "C"], "rows": [["1", "2", "3"], ["4", "5", "6"]]}, "key_fact": "Sonuç."},
    {"title": "Göstergeler", "layout": "kpi_grid", "kpis": [{"value": "349 TL", "label": "Fiyat"}, {"value": "140 TL", "label": "Maliyet"}], "bullets": ["a", "b"], "key_fact": "Marj."},
    {"title": "Sonuç ve adımlar", "layout": "closing", "bullets": ["Eğitim: her yıl", "Parola: yönetici", "Bildirim: hızlı"], "key_fact": "Alışkanlık."},
]


def test_every_layout_builds_a_valid_deck(tmp_path: Path):
    out = dr.build_pptx_presentation("Test Sunumu", "Alt başlık", SLIDES, tmp_path / "d.pptx", language="tr")
    prs = Presentation(str(out))
    assert len(prs.slides) == len(SLIDES) + 1
    kinds = [{sh.shape_type for sh in s.shapes} for s in list(prs.slides)[1:]]
    assert all(kinds)
    assert any(getattr(sh, "has_chart", False) and sh.has_chart for sh in prs.slides[2].shapes)
    assert any(getattr(sh, "has_table", False) and sh.has_table for sh in prs.slides[5].shapes)


def test_bullets_are_real_hanging_bullets(tmp_path: Path):
    out = dr.build_pptx_presentation("T", "S", SLIDES[:1], tmp_path / "b.pptx", language="tr")
    xml = Presentation(str(out)).slides[1].shapes._spTree.xml
    assert "buChar" in xml and 'indent="-' in xml


def test_slide_count_parser_handles_hyphen_and_english():
    assert dr._parse_slide_count("Create a 6-slide deck") == 5
    assert dr._parse_slide_count("8 slaytlık sunum") == 7
    assert dr._parse_slide_count("a 10 slides overview") == 9


def test_outline_acceptance_counts_table_and_chart_slides_and_ignores_comparison_signs():
    spec = {"slides": [
        {"title": "A", "table": {"headers": ["x", "y"], "rows": [["1", "2"]]}},
        {"title": "B", "chart": {"labels": ["a", "b"], "values": [1, 2]}},
        {"title": "C", "bullets": ["süre < 1 saat olmalı", "x"]},
        {"title": "D", "columns": {"left_bullets": ["l"], "right_bullets": ["r"]}},
    ]}
    assert dr._slides_are_real(spec, "konu sunumu")
    spec["slides"][2]["bullets"] = ["<kaynaktaki değer> kadar"]
    assert not dr._slides_are_real(spec, "konu sunumu")
