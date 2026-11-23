"""Verification tests for Turkish Unicode PDF/DOCX/XLSX generation and zero-hallucination file inspection."""

from __future__ import annotations

import io
from pathlib import Path

from openpyxl import Workbook, load_workbook

import document_factory as df
import extract
import file_inspector as fi

TURKISH_PANGRAM = "Pijamalı hasta yağız şoföre çabucak güvendi - ÇĞİÖŞÜ çğıöşü"


def test_pdf_preserves_all_turkish_characters_and_paginates(tmp_path: Path):
    out_pdf = tmp_path / "turkce_rapor.pdf"
    rows = [[f"{i:02d}", f"İşlem Şablonu {i} (Ğ/Ş/İ)", "Ölçüm", i * 150] for i in range(1, 35)]
    df._build_pdf(
        out_pdf,
        title=f"Türkçe Mühendislik Raporu - {TURKISH_PANGRAM[:24]}",
        summary=TURKISH_PANGRAM,
        sections=[{"heading": "1. Şirket Değerlendirmesi ve Ölçümler", "content": TURKISH_PANGRAM}],
        headers=["No", "İşlem Adı", "Bölüm", "Tutar (TL)"],
        rows=rows,
    )
    assert out_pdf.is_file() and out_pdf.stat().st_size > 2000
    extracted = extract.extract_pdf_text(out_pdf.read_bytes())
    for ch in ("ğ", "ş", "ı", "İ", "ö", "ü", "ç", "Ğ", "Ş"):
        assert ch in extracted, f"Missing Turkish char '{ch}' in extracted PDF: {extracted[:300]}"
    assert "Sayfa 2 /" in extracted


def test_xlsx_and_docx_turkish_rich_tables_and_formulas(tmp_path: Path):
    out_xlsx = tmp_path / "turkce_tablo.xlsx"
    out_docx = tmp_path / "turkce_belge.docx"
    rows = [
        ["01", "Rulman Yatağı Flanşı", "İmalat", 12500],
        ["02", "Yüzey Taşlama İşlemi", "Kalite", 8400],
        ["03", "Ölçüm ve Sertifikasyon", "AS9102", 4100],
    ]
    df._build_xlsx(
        out_xlsx,
        title="Üretim Maliyet Tablosu",
        summary=TURKISH_PANGRAM,
        sections=[{"heading": "Özet Notlar", "content": TURKISH_PANGRAM}],
        headers=["Kod", "İşlem Açıklaması", "Birim", "Maliyet (TL)"],
        rows=rows,
    )
    wb = load_workbook(out_xlsx, data_only=False)
    assert "Veri ve Tablo" in wb.sheetnames
    assert "Yönetici Özeti ve Notlar" in wb.sheetnames
    ws = wb["Veri ve Tablo"]
    assert ws["B5"].value == "Rulman Yatağı Flanşı"
    assert "=SUM(" in str(ws["D8"].value)
    assert "=AVERAGE(" in str(ws["D9"].value)
    assert len(ws._charts) == 1

    df._build_docx(
        out_docx,
        title="Türkçe Kurumsal Şartname",
        summary=TURKISH_PANGRAM,
        sections=[{"heading": "1. Ölçüm Standartları", "content": TURKISH_PANGRAM}],
        headers=["Kod", "İşlem", "Birim", "Maliyet"],
        rows=rows,
    )
    docx_txt = extract.extract_docx_text(out_docx.read_bytes())
    assert "Rulman Yatağı Flanşı" in docx_txt and "yağız şoföre" in docx_txt


def test_extract_handles_windows_cp1254_turkish_csv():
    raw_cp1254 = "Ürün;Açıklama;Fiyat\nÇelik Flanş;Yağlı işleme;1500\n".encode("cp1254")
    txt = extract.extract_csv_text(raw_cp1254)
    assert "Çelik Flanş" in txt and "Yağlı işleme" in txt


def test_file_inspector_catches_real_bugs_without_hallucination():
    # 1. Python syntax + security error
    py_bad = b"def hesapla(x):\n    if x > 0\n        return eval(x)\n"
    r_py = fi.inspect_uploaded_file("bozuk.py", py_bad)
    assert r_py["ok"] is False
    types_py = {i["type"] for i in r_py["issues"]}
    assert "SYNTAX_ERROR" in types_py

    # 2. Invalid JSON
    r_json = fi.inspect_uploaded_file("ayar.json", b'{"ad": "CNC", "deger": }')
    assert r_json["ok"] is False
    assert r_json["issues"][0]["type"] == "JSON_SYNTAX_ERROR"

    # 3. Unclosed HTML tag & missing charset
    r_html = fi.inspect_uploaded_file("sayfa.html", b"<html><body><div><p>Merhaba</div></body></html>")
    types_html = {i["type"] for i in r_html["issues"]}
    assert "MISSING_CHARSET" in types_html
    assert "MISMATCHED_TAG" in types_html

    # 4. CSV column mismatch
    r_csv = fi.inspect_uploaded_file("veri.csv", "ad,deger\nA,10\nB,20,FAZLA\n".encode())
    assert any(i["type"] == "CSV_COLUMN_MISMATCH" and i["line"] == 3 for i in r_csv["issues"])

    # 5. Excel formula error (#DIV/0! and #REF!)
    wb = Workbook()
    ws = wb.active
    ws["A1"] = "Sonuc"
    ws["A2"] = "#DIV/0!"
    ws["B2"] = "#REF!"
    buf = io.BytesIO()
    wb.save(buf)
    r_xlsx = fi.inspect_uploaded_file("hatali.xlsx", buf.getvalue())
    assert r_xlsx["ok"] is False
    assert sum(1 for i in r_xlsx["issues"] if i["type"] == "EXCEL_FORMULA_ERROR") == 2
