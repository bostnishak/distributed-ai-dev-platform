"""Deck rubric: what counts as a 90+ deck and what is penalised."""

from __future__ import annotations

import pytest

import deck_score

pytestmark = pytest.mark.unit


def _slide(title, layout="bullets", n=3, **kw):
    return {"title": title, "layout": layout, "bullets": [f"Madde {i} metni burada" for i in range(n)], "key_fact": "Tek cümlelik çıkarım burada.", "notes": "Bu slayt için yeterince uzun bir konuşmacı notu yazıldı.", **kw}


def _good():
    layouts = ["bullets", "two_column", "steps", "table", "kpi_grid", "closing"]
    return {"slides": [_slide(f"Siber güvenlik başlığı {i}", lay) for i, lay in enumerate(layouts)]}


def test_a_full_varied_deck_scores_high():
    score, issues = deck_score.score(_good(), "7 slaytlık siber güvenlik sunumu hazırla")
    assert score >= 90 and issues == []


def test_wrong_slide_count_thin_slides_and_repeats_are_penalised():
    deck = {"slides": [_slide("Siber başlık bir"), _slide("Siber başlık iki"), _slide("Siber başlık üç", n=1), _slide("Siber başlık dört", n=1), _slide("Siber başlık beş")]}
    score, issues = deck_score.score(deck, "8 slaytlık siber güvenlik sunumu hazırla")
    assert score < 75 and any("8 slayt istenmiş" in i for i in issues) and any("3'ten az" in i for i in issues) and any("düzen" in i for i in issues)


def test_english_count_phrase_and_language_mismatch():
    deck = {"slides": [_slide("Şirket tanıtım başlığı", "bullets", ch="ç") for _ in range(2)]}
    _score, issues = deck_score.score(deck, "Create a 6-slide company introduction deck in English")
    assert any("6 slayt" in i for i in issues)
    deck = {"slides": [{**_slide("Şirket tanıtımı çok güzel başlık"), "bullets": ["Şirket çalışanları için çözümler üretir", "Müşteri memnuniyeti önceliğimizdir", "Güçlü ağ ve deneyim"]} for _ in range(5)]}
    assert any("İngilizce istenmiş" in i for i in deck_score.score(deck, "Create a 6-slide company deck in English")[1])


def test_invented_statistics_and_placeholders_are_found():
    deck = _good()
    deck["slides"][1]["bullets"][0] = "Saldırıların %72'si e-postayla gelir"
    deck["slides"][2]["title"] = "<Başlık> metni"
    issues = deck_score.score(deck, "7 slaytlık siber güvenlik sunumu")[1]
    assert any("istatistik" in i for i in issues) and any("yer tutucu" in i for i in issues)
