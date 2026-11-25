"""Posters show only what the user wrote; nothing is invented to fill the layout."""

from __future__ import annotations

import asyncio

import pytest

import poster_icons
import poster_layout
import poster_palettes
import poster_studio as ps

pytestmark = pytest.mark.unit

PAL = {"mono_bw": {k: "#111111" for k in ("bg1", "bg2", "bg3", "primary", "secondary", "accent", "text", "muted", "card", "grid")}}
PAL["crimson_carbon"] = PAL["mono_bw"]


async def _llm_inventing(_system: str, _user: str) -> dict:
    return {"title": "Tuz Kafe", "slogan": "Lezzetli anlar", "kicker": "ÖZEL ETKİNLİK", "date": "15 MAYIS 2024", "location": "ANKARA", "tags": ["BISTRO", "KEYNOTE"]}


def _spec(prompt: str) -> dict:
    return asyncio.run(ps.build_spec(prompt, "mono_bw", _llm_inventing, "m"))


def test_invented_fields_are_dropped_and_user_slogan_wins():
    spec = _spec("'Tuz Kafe' için siyah beyaz minimal bir afiş yap; sloganı 'Her yudumda deniz' olsun")
    assert spec["title"] == "TUZ KAFE" and spec["slogan"] == "Her yudumda deniz"
    assert spec["kicker"] == spec["date"] == spec["location"] == "" and spec["tags"] == []


def test_fields_the_user_wrote_are_kept():
    spec = _spec("Tuz Kafe açılış afişi: 15 Mayıs 2024, Ankara, etkinlik: BISTRO")
    assert spec["date"] and spec["location"] == "ANKARA" and spec["tags"] == ["BISTRO"]


def test_turkish_upper_case():
    assert ps.tr_upper("lezzetli anlar") == "LEZZETLİ ANLAR" and ps.tr_upper("ışık") == "IŞIK"


def test_render_omits_missing_elements():
    svg = poster_layout.render(_spec("'Tuz Kafe' afiş sloganı 'Her yudumda deniz'"), PAL, str, "Arial")
    assert "TUZ KAFE" in svg and "Her yudumda deniz" in svg
    assert "KEYNOTE" not in svg and "ÖZEL ETKİNLİK" not in svg and "İSTANBUL" not in svg


def test_lineup_stops_at_quotes_and_keeps_band_names_whole():
    f = ps.pattern_fields("Festival: 15 Temmuz 2027, İzmir Kültürpark, sanatçılar: Duman, Mor ve Ötesi, 'Yaz' başlıklı")
    assert f["tags"] == ["Duman", "Mor ve Ötesi"] and f["location"].startswith("İzmir")


def test_english_is_not_turkish_upper_cased():
    assert not ps.is_turkish("Poster for 'Night Run' charity race") and ps.is_turkish("Işık festivali afişi")


def test_palette_ignores_quoted_words_and_combines_navy_gold():
    keys = ["a", "b"]
    assert poster_palettes.pick("slogan 'light' lacivert ve altın", 0, keys) == "navy_gold"
    assert poster_palettes.pick("'Mavi Ay' afişi kırmızı", 0, keys) == "crimson_carbon"


def test_icons_follow_the_subject():
    assert poster_icons.pick("Night Run 5K charity race")[0] == "runner"
    assert poster_icons.pick("güneş enerjisi semineri")[0] == "sun"
    assert poster_icons.pick("zzz") == ["star"]
