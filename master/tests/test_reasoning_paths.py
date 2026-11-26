"""Reasoning helpers: puzzle detection, vocabulary hint and the English-drift check."""

from __future__ import annotations

import pytest

import reasoning_mode as rm

pytestmark = pytest.mark.unit


def test_puzzles_go_to_the_reasoner_but_calculations_do_not():
    assert rm._PUZZLE_RE.search("Üç kutu var, etiketler yanlış")
    assert rm._PUZZLE_RE.search("A der ki: ben yalancıyım")
    assert not rm._PUZZLE_RE.search("Bir havuzu A musluğu 6 saatte doldurur, kaç saatte dolar?")


def test_vocabulary_hint_keeps_question_words():
    assert "şövalye" in rm._vocab("Adada şövalyeler ve yalancılar yaşar")


def test_english_drift_is_detected():
    assert rm._english_ratio("If an apple is drawn then the box contains only apples") > 0.2
    assert rm._english_ratio("Elma çekilirse bu kutuda sadece elma vardır") < 0.06
