"""v5 milestone 11: four deliverables built from one set of numbers, read back and compared to the last decimal."""

from __future__ import annotations

from decimal import Decimal

import pytest

import consistency
import consistency_files
import office_verify

pytestmark = pytest.mark.integration

ASK = "Depo gideri; koli 120 x 4,50; bant 35 x 12,75; streç film 7 x 189,99; çift taraflı yapışkan etiket rulosu 1250 x 0,35; yarım kuruş 3 x 0,335; kdv 20"


def test_request_is_parsed_and_computed_exactly():
    report = consistency.parse(ASK)
    assert report.title == "Depo gideri" and [i.name for i in report.items][-1] == "yarım kuruş" and report.vat == 20
    values = consistency.figures(report)
    assert values["yarım kuruş"] == Decimal("1.01"), "3 x 0,335 = 1,005 yukarı yuvarlanır (ikili kayan noktayla 1,00 çıkardı)"
    assert values["Ara toplam"] == Decimal("2754.69") and values["KDV"] == Decimal("550.94") and values["Genel toplam"] == Decimal("3305.63")
    assert consistency.turkish(Decimal("1234567.5")) == "1.234.567,50" and consistency.read_turkish("1.234.567,50 TL") == Decimal("1234567.50")
    assert consistency.parse("yalnız başlık") is None and consistency.parse("a 1 x 2; a 3 x 4") is None


def test_any_difference_or_missing_figure_is_named():
    reference = {"a": Decimal("1.00"), "b": Decimal("2.50")}
    found = consistency.mismatches(reference, {"pdf": {"a": Decimal("1"), "b": Decimal("2.51")}, "web": {"a": Decimal("1.00")}})
    assert found == ["pdf: 'b' 2.51 yazıyor, doğrusu 2.50", "web: 'b' yok"]


def _delivered(tmp_path):
    if not office_verify.soffice():
        pytest.skip("LibreOffice yok")
    report = consistency.parse(ASK)
    try:
        files, differences, sources = consistency.deliver(report, tmp_path)
    except Exception as exc:  # no usable browser on this machine
        if "Executable doesn't exist" in str(exc) or "chrome" in str(exc).lower():
            pytest.skip("tarayıcı yok")
        raise
    return report, files, differences, sources


def test_four_deliverables_agree_to_the_last_decimal(tmp_path):
    report, files, differences, sources = _delivered(tmp_path)
    assert differences == [] and set(sources) == {"excel", "sunum", consistency.CHART, "pdf", "web"}
    assert all(len(values) == len(consistency.figures(report)) for name, values in sources.items() if name != consistency.CHART)
    assert len(sources[consistency.CHART]) == len(report.items)
    assert office_verify.check(files["excel"]) == [], "formüller hatasız yeniden hesaplanır"
    pictures = consistency_files.render_pngs(files, tmp_path / "png")
    assert {p.name for p in pictures} == {"excel.png", "sunum.png", "pdf.png", "web.png"} and all(p.stat().st_size > 2000 for p in pictures)


def test_a_tampered_file_is_caught(tmp_path):
    from openpyxl import load_workbook
    from pptx import Presentation

    report, files, _differences, _sources = _delivered(tmp_path)
    book = load_workbook(files["excel"])
    book.active["D2"] = 541
    book.save(files["excel"])
    deck = Presentation(files["sunum"])
    table = next(s for s in deck.slides[0].shapes if s.has_table).table
    table.cell(2, 1).text = "999,00"
    deck.save(files["sunum"])
    found = consistency.mismatches(consistency.figures(report), consistency_files.read_all(report, files))
    assert any(line.startswith("excel: 'koli' 541") for line in found) and any(line.startswith("excel: 'Ara toplam'") for line in found)
    assert any(line.startswith("sunum: 'bant' 999") for line in found), "grafik doğru olsa da tablodaki yanlış sayı yakalanır"
    assert not any(line.startswith(("pdf:", "web:")) for line in found)
