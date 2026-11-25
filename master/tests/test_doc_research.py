"""Factual documents get a code-written Kaynakça from real sources; contracts and letters do not trigger research."""

from __future__ import annotations

import asyncio

import pytest

import doc_research

pytestmark = pytest.mark.unit


def test_contracts_and_letters_skip_research():
    assert not doc_research.wants_research("kira sözleşmesi hazırla")
    assert doc_research.wants_research("rüzgar enerjisi hakkında 3 sayfalık rapor PDF hazırla")


def test_bibliography_lists_only_given_sources():
    blocks = doc_research.bibliography([{"title": "TEİAŞ Raporu", "url": "https://example.org/r"}])
    assert blocks[0]["text"] == "Kaynakça"
    assert "https://example.org/r" in blocks[1]["items"][0]
    assert doc_research.bibliography([]) == []


def test_gather_without_network_returns_nothing(monkeypatch):
    import research_context

    monkeypatch.setattr(research_context, "build", lambda *_a: ([], "note"))
    sources, note = asyncio.run(doc_research.gather("enerji raporu hazırla"))
    assert sources == [] and "UYDURMA" in note  # no sources: the model is told not to invent country-level figures
