"""The reference list is written by code: real sources only, model-made lists replaced, no fake citation."""

from __future__ import annotations

import pytest

import answer_sources as asrc

pytestmark = pytest.mark.unit

SRC = [{"id": "S1", "title": "Bir", "url": "https://a.example"}, {"id": "S2", "title": "İki", "url": "https://b.example"}, {"id": "S3", "title": "Üç", "url": "https://c.example"}]


def test_only_cited_sources_are_listed_and_models_own_list_is_replaced():
    out = asrc.finalize("Bilgi [S1] ve [S3].\n\n### Kaynaklar\n- uydurma kaynak", SRC, True)
    assert "uydurma" not in out and "[S1] Bir" in out and "[S3] Üç" in out and "[S2]" not in out


def test_uncited_answer_lists_all_sources():
    out = asrc.finalize("Atıfsız cevap.", SRC, True)
    assert out.count("https://") == 3


def test_no_sources_means_honest_note_and_no_citation_marks():
    out = asrc.finalize("Genel bilgi [S1].", [], True)
    assert "[S1]" not in out.split("Not:")[0] and "doğrulanmamıştır" in out and "### Kaynaklar" not in out


def test_plain_chat_is_untouched():
    assert asrc.finalize("Merhaba", [], False) == "Merhaba"
