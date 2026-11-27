"""Layered summaries, Typst documents, audience and time budget, first-token timing and nightly consolidation."""

import asyncio
import json

import pytest

import doc_tree
import pacing
import typst_render
from gateway import first_token

pytestmark = pytest.mark.unit


def test_summary_tree_covers_every_line_and_drops_invented_numbers():
    lines = [f"Satır {i}: depo düzeni ve sayım süreci anlatılır, ekip haftada bir toplanır." for i in range(500)]
    lines[300] = "Yıllık kira bedeli 480000 TL olarak belirlenmiştir."
    text = "\n".join(lines)

    async def chat(system, user, schema):
        if "belge parçasını" in system:
            quote = "Yıllık kira bedeli 480000 TL olarak belirlenmiştir." if "480000" in user else "uydurma alıntı cümlesi burada yok"
            return json.dumps({"summary": "Parça süreçleri anlatır. Bütçe 999999 TL ayrılmıştır", "quotes": [quote]})
        return json.dumps({"summary": "Belge depo süreçlerini anlatır"})

    async def run():
        return [e async for e in doc_tree.summarise(text, chat)]

    report = asyncio.run(run())[-1][1]
    assert "999999" not in report and "satır 301" in report and "uydurma alıntı" not in report
    assert "Satır 1-" in report and "-500:**" in report


def test_typst_escapes_content_and_produces_pages(tmp_path):
    pytest.importorskip("typst")
    spec = {"title": "Deneme #eval(\"1\")", "subtitle": "", "blocks": [
        {"type": "heading", "text": "Giriş $x$", "level": 1}, {"type": "para", "text": "Fiyat = 5 * 3 [TL] @kaynak #read(\"/etc/passwd\")"},
        {"type": "bullets", "items": ["a_b", "c<d>"]}, {"type": "table", "headers": ["Ad", "Tutar"], "rows": [["x", "10"]], "caption": ""}]}
    assert "\\#read" in typst_render.source(spec) and "\n#read" not in typst_render.source(spec)
    path = tmp_path / "a.pdf"
    assert typst_render.build(path, spec) >= 1 and path.read_bytes().startswith(b"%PDF")
    import pymupdf

    with pymupdf.open(path) as doc:
        text = doc[0].get_text()
    assert "#read(" in text and "5 * 3 [TL]" in text
    assert typst_render.wanted("denklem içeren rapor pdf") and not typst_render.wanted("kira sözleşmesi pdf")


def test_audience_only_when_the_message_says_so():
    assert "konuya yeni" in pacing.audience_note("bunu basitçe anlat")
    assert "uzman" in pacing.audience_note("ileri düzey teknik detay ver")
    assert "acelesi" in pacing.audience_note("acil: kısaca söyle")
    assert pacing.audience_note("Ankara'nın nüfusu kaç?") == ""


def test_time_budget_speaks_only_after_it_is_passed():
    assert pacing.overrun_note("bir stok uygulaması yap", 10) == ""
    assert "devam et" in pacing.overrun_note("bir stok uygulaması yap", 4000)


def test_first_token_median(tmp_path, monkeypatch):
    monkeypatch.setattr(first_token, "_path", lambda: tmp_path / "f.jsonl")
    for ms in (100, 900, 300):
        first_token.note("m", 0.0, ms / 1000)
    assert first_token.medians() == {"m": 300}


def test_memory_view_route(monkeypatch):
    from fastapi.testclient import TestClient

    import app as app_module
    import workspace_inspect

    monkeypatch.setattr(workspace_inspect.preferences, "load", lambda user: [{"text": "Gradyan kullanma", "at": "2026-11-27"}])
    body = TestClient(app_module.app).get("/api/studio/memory-view").json()
    assert body["preferences"][0]["text"] == "Gradyan kullanma" and isinstance(body["facts"], list)


def test_a_part_that_cannot_be_summarised_is_named_not_dropped():
    text = "\n".join(f"Satır {i}: depo düzeni ve sayım süreci anlatılır, ekip haftada bir toplanır." for i in range(500))
    seen = []

    async def chat(system, user, schema):
        if "belge parçasını" in system:
            seen.append(1)
            return "bozuk" if len(seen) == 1 else json.dumps({"summary": "Parça süreçleri anlatır"})
        return json.dumps({"summary": "Belge süreçleri anlatır"})

    async def run():
        return [e async for e in doc_tree.summarise(text, chat)]

    report = asyncio.run(run())[-1][1]
    assert "Satır 1-" in report and "1 parça özetlenemedi" in report
