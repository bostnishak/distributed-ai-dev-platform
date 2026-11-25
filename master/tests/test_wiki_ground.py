"""Factual questions are grounded in a quoted Wikipedia extract; everything else is left alone."""

from __future__ import annotations

import pytest

import wiki_ground

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("q", ["Mustafa Kemal Atatürk kimdir?", "Fransa'nın başkenti neresi?", "Who is Alan Turing?", "Eyfel Kulesi ne zaman yapıldı?"])
def test_factual_questions_are_detected(q):
    assert wiki_ground.looks_factual(q)


@pytest.mark.parametrize("q", ["Bana bir python kodu yaz, nedir diye sorma", "Sunum hazırla: Türkiye nüfusu", "merhaba", "bir şiir yaz kimdir kimdi", "a\nb nedir"])
def test_non_factual_requests_are_skipped(q):
    assert not wiki_ground.looks_factual(q)


def test_lookup_builds_cited_note(monkeypatch):
    monkeypatch.setattr(wiki_ground, "_fetch", lambda lang, terms: ("Türkiye", "Ankara Türkiye'nin başkentidir.", "https://tr.wikipedia.org/wiki/Ankara"))
    sources, note = wiki_ground.lookup("Türkiye'nin başkenti neresi?")
    assert sources[0]["id"] == "S1" and "Ankara" in note and "uydurma" in note


def test_no_hit_leaves_prompt_untouched(monkeypatch):
    monkeypatch.setattr(wiki_ground, "_fetch", lambda lang, terms: None)
    assert wiki_ground.lookup("Zzqx nedir?") == ([], "")


def test_search_terms_drop_question_words():
    assert wiki_ground._search_terms("Alan Turing kimdir?") == "Alan Turing"
