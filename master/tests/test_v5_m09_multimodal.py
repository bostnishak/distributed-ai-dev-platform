"""v5 milestone 09: messy PDFs and scans, ugly spreadsheets, recordings and the cited inbox, on real generated files."""

from __future__ import annotations

import asyncio
import datetime as dt
import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest

import codeswitch
import extract
import inbox
import ingest_pdf
import multimodal_samples as samples
import ocr_engine
import sheet_infer

pytestmark = pytest.mark.unit

_VOICE = Path(__file__).resolve().parents[1] / "data" / "voices" / "tr_TR-dfki-medium.onnx"
_HAS_SPEECH = _VOICE.is_file() and all(importlib.util.find_spec(m) for m in ("piper", "faster_whisper", "av"))


def test_columns_are_read_one_after_the_other_and_tables_keep_merged_cells():
    found, warnings = ingest_pdf.blocks(samples.two_column_pdf())
    text = "\n".join(b.text for b in found)
    assert warnings == []
    assert text.index("Sol sütun paragraf 3") < text.index("Sağ sütun paragraf 1"), "sol sütun bitmeden sağa geçilmez"
    table = next(b for b in found if b.kind == "tablo")
    assert "| Hat A | Ocak | 120 |" in table.text and "| Hat A | Şubat | 135 |" in table.text
    assert any(b.kind == "formül" and "Verim" in b.text for b in found)
    assert all(b.page == 1 and b.box[2] > b.box[0] and b.box[3] > b.box[1] for b in found)


@pytest.mark.parametrize("turned", [0, 90])
def test_scanned_page_is_read_with_turkish_letters_even_sideways(turned):
    if not ocr_engine.available():
        pytest.skip("OCR modeli yok")
    found, warnings = ingest_pdf.blocks(samples.scanned_pdf(turned))
    text = " ".join(b.text for b in found)
    assert warnings == [] and all(b.kind == "ocr" for b in found)
    for word in ("Depo Teslim", "Ayşe", "Yılmaz", "Şişe", "kapağı", "1.250", "ağırlık", "842,5", "uygun", "iğne"):  # a final "ı" is sometimes read as "i"
        assert word in text, f"{word!r} okunamadı: {text}"
    assert "Ayşe" in extract.extract_pdf_text(samples.scanned_pdf())


def test_scan_without_a_model_is_reported_not_skipped(monkeypatch):
    monkeypatch.setattr(ocr_engine, "available", lambda: False)
    found, warnings = ingest_pdf.blocks(samples.scanned_pdf())
    assert found == [] and "taranmış" in warnings[0]


def test_messy_workbook_becomes_a_typed_table_with_cell_places():
    table = sheet_infer.from_xlsx(samples.messy_workbook())[0]
    assert table.header == ["Bölge", "Tarih", "Ürün", "Tutar", "Adet"] and table.types == ["metin", "tarih", "metin", "sayı", "sayı"]
    assert [row[0] for row in table.rows] == ["Marmara", "Marmara", "Ege"]
    assert table.rows[2][3] == Decimal("12480.75") and table.rows[2][4] == Decimal("1250") and table.rows[0][1] == dt.date(2026, 1, 3)
    assert table.cell(2, 3) == "Satış!E6" and any("3. satırda" in note for note in table.notes)
    assert "Tutar toplamı = 14711.25" in sheet_infer.markdown([table])


def test_us_and_ambiguous_number_styles_are_told_apart():
    american = sheet_infer.from_csv('name,amount\nA,"1,250.50"\nB,3.25\n')[0]
    assert american.types[1] == "sayı" and american.rows[0][1] == Decimal("1250.50")
    unclear = sheet_infer.from_csv("ad;miktar\nA;1.250\nB;2.500\n")[0]
    assert unclear.types[1] == "metin" and "belli değil" in unclear.notes[0]
    mixed = sheet_infer.from_csv('ad;miktar\nA;"1.250,50"\nB;"1,250.50"\n')[0]
    assert mixed.types[1] == "metin" and "karışık" in mixed.notes[0]


@pytest.mark.skipif(not _HAS_SPEECH, reason="konuşma modeli ya da kütüphaneleri yok")
def test_speech_is_transcribed_with_times(tmp_path):
    import media_index

    segments = media_index.transcribe(samples.speech(tmp_path / "toplanti.wav", _VOICE), language="tr")
    said = " ".join(s.text for s in segments).lower()
    assert "bakım" in said and "mehmet" in said and segments[0].start < segments[-1].end


def test_video_scene_changes_are_kept_with_their_times(tmp_path):
    if not importlib.util.find_spec("av"):
        pytest.skip("av yok")
    import media_index

    frames = media_index.keyframes(samples.video(tmp_path / "ekran.mp4"), tmp_path / "kareler")
    assert [round(moment) for moment, _ in frames] == [0, 3, 6]
    assert all((tmp_path / "kareler" / name).stat().st_size > 200 for _m, name in frames)
    assert media_index.clock(3725) == "1:02:05"


def test_inbox_answers_only_with_real_places_and_numbers(tmp_path, monkeypatch):
    monkeypatch.setattr(inbox.config, "data_dir", lambda: tmp_path)
    (inbox.folder() / "sevkiyat.xlsx").write_bytes(samples.messy_workbook())
    (inbox.folder() / "rapor.pdf").write_bytes(samples.two_column_pdf())
    replies = iter(["Tutar toplamı 99999 [1].", "Tutar toplamı 14711.25 TL [T]."])
    asked: list[str] = []

    async def model(system, user):
        asked.append(user)
        number = next(line.split("]")[0][1:] for line in user.splitlines() if "Tutar toplamı=14711.25" in line)
        return next(replies).replace("[T]", f"[{number}]")

    reply = asyncio.run(inbox.answer("sevkiyat tutar toplamı kaç?", model))
    assert "14711.25" in reply and "**Kaynaklar**" in reply and "sevkiyat.xlsx, Satış sütun E" in reply
    assert "REDDEDİLDİ" in asked[1] and "99999" in asked[1]
    assert "rapor.pdf" in inbox.listing() and inbox.question_of("inbox") == "" and inbox.question_of("inbox: ne var?") == "ne var?"
    assert inbox.question_of("inbox klasörü nedir") is None


def test_untrustworthy_answers_are_named():
    given = [inbox.Source("a.pdf", "sayfa 1", "Koli sayısı 1.250 adet")]
    assert inbox.problems("1250 koli [1].", given) == []
    assert "hiç kaynak" in inbox.problems("1250 koli.", given)[0]
    assert "olmayan kaynak" in inbox.problems("1250 koli [4].", given)[0]
    assert "olmayan sayı" in inbox.problems("2000 koli [1].", given)[0]
    assert inbox.problems("Kaynaklarda bunu bulamadım.", given) == []


def test_mixed_language_request_keeps_technical_names():
    ask = "sidebar'daki filtre butonunun state'ini SQLite'a bağla, userList component'ini güncelle"
    assert codeswitch.terms(ask)[:4] == ["sidebar", "state", "SQLite", "userList"]
    assert "toLocaleLowerCase('tr')" in codeswitch.note(ask) and "userList" in codeswitch.note(ask)
    assert codeswitch.note("Bana bir şiir yaz") == "" and codeswitch.note("add a sidebar component") == ""
