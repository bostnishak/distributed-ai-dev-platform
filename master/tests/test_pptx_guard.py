"""Deck outlines: invented statistics are dropped unless the user supplied numbers; length is capped."""

import pytest

from pptx_guard import clean_spec

pytestmark = pytest.mark.unit


def _spec():
    return {"slides": [
        {"title": "A", "layout": "bullets", "bullets": ["Çalışanların %81'i risk altında", "Eğitim önemlidir"], "key_fact": "%90 artış"},
        {"title": "B", "layout": "kpi_grid", "kpis": [{"value": "%65", "label": "Önleme"}], "bullets": []},
        {"title": "C", "layout": "closing", "bullets": ["Sürekli eğitim verin"]},
    ]}


def test_invented_numbers_removed_without_source_numbers():
    out = clean_spec(_spec(), "siber güvenlik sunumu", 6)["slides"]
    assert out[0]["bullets"] == ["Eğitim önemlidir"] and out[0]["key_fact"] == ""
    assert out[1]["layout"] == "bullets" and out[1]["bullets"] == ["Önleme"]


def test_numbers_kept_when_user_gave_numbers():
    out = clean_spec(_spec(), "Q1 %12 büyüme ile sunum", 6)["slides"]
    assert "%81" in out[0]["bullets"][0] and out[1]["layout"] == "kpi_grid"


def test_slide_count_capped_keeping_closing():
    out = clean_spec(_spec(), "x 1", 2)["slides"]
    assert [s["title"] for s in out] == ["A", "C"]


def test_slide_count_phrase_is_not_source_data():
    out = clean_spec(_spec(), "6 slaytlık siber güvenlik sunumu", 6)["slides"]
    assert out[0]["bullets"] == ["Eğitim önemlidir"]
