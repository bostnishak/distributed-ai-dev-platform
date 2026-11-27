"""Whole-document reading with line-anchored quotes, and the second research round."""

import asyncio
import json

import pytest

import doc_reader
import research

pytestmark = pytest.mark.unit


def _document():
    lines = [f"Bölüm {i}: sıradan bir açıklama satırı ve ayrıntılar burada yer alır." for i in range(400)]
    lines[10] = "Birinci depo kirası aylık 12000 TL olarak ödenir."
    lines[390] = "İkinci depo kirası aylık 8000 TL olarak ödenir."
    return "\n".join(lines)


def test_nothing_is_left_out_and_quotes_get_line_numbers():
    text = _document()
    pieces = doc_reader.parts(text)
    assert len(pieces) > 2 and "\n".join(pieces) == text
    assert doc_reader.line_of(text, "İkinci depo kirası aylık 8000 TL") == 391


def test_facts_far_apart_are_both_found_and_cited():
    text = _document()

    async def chat(system, user, schema):
        if "SAYFA METNİ" in user:
            claims = [{"claim": f"kira {n} TL", "quote": f"{w} depo kirası aylık {n} TL olarak ödenir."} for w, n in (("Birinci", 12000), ("İkinci", 8000)) if f"{w} depo" in user]
            return json.dumps({"claims": claims})
        return json.dumps({"summary": [{"text": "Kiralar 12000 TL ve 8000 TL", "ids": [1, 2]}, {"text": "Toplam 99999 TL", "ids": [1]}]})

    async def run():
        return [e async for e in doc_reader.answer("tüm belgedeki kiraları ver", text, chat)]

    report = asyncio.run(run())[-1][1]
    assert "satır 11" in report and "satır 391" in report and "99999" not in report and "[1][2]" in report


@pytest.mark.parametrize(("prompt", "length", "wanted"), [
    ("belgenin tamamını oku ve kiraları listele", 40000, True), ("bu belgeyi özetle", 40000, False), ("tüm belgeyi oku", 500, False),
])
def test_only_long_whole_document_requests(prompt, length, wanted):
    assert doc_reader.wants_whole(prompt, "a.pdf", length) == wanted


def test_open_questions_start_a_second_round(monkeypatch):
    pages = {"q1": ("https://a.example/1", "A", "Birinci sayfa: ürün 2024 yılında çıktı ve çok satıldı." * 6),
             "fiyat nedir": ("https://b.example/2", "B", "İkinci sayfa: ürünün fiyatı 500 TL olarak açıklandı." * 6)}
    searched = []
    monkeypatch.setattr(research.research_context, "web_enabled", lambda: True)

    async def gather(queries, run):
        searched.append(list(queries))
        return [pages[q] for q in queries]

    monkeypatch.setattr(research, "_gather", gather)
    reports = []

    async def chat(system, user, schema):
        if "alt sorguya" in system:
            return '{"queries": ["q1"]}'
        if "SAYFA METNİ" in user:
            quote = "ürünün fiyatı 500 TL olarak açıklandı." if "İkinci sayfa" in user else "ürün 2024 yılında çıktı ve çok satıldı."
            return json.dumps({"claims": [{"claim": quote, "quote": quote}]})
        reports.append(user)
        return json.dumps({"summary": [{"text": "bulgular", "ids": [1]}], "open_questions": ["fiyat nedir"] if len(reports) == 1 else []})

    async def run():
        return [e async for e in research.investigate("derin araştır: ürün", chat)]

    events = asyncio.run(run())
    assert searched == [["q1"], ["fiyat nedir"]] and len(reports) == 2 and "500 TL" in reports[1]
    assert "2 sayfa okundu" in events[-1][1]
