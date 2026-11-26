"""Table totals are recomputed, duplicated units collapse, unrequested signature blocks go, absurd amounts lower the score."""

from __future__ import annotations

import pytest

import deliverable_score
import doc_polish

pytestmark = pytest.mark.unit


def test_total_row_is_the_real_sum():
    blocks = [{"type": "table", "rows": [["A", "10.000 TL"], ["B", "25.000 TL"], ["Toplam", "99.000 TL"]]}]
    doc_polish.fix_totals(blocks)
    assert blocks[0]["rows"][-1][1] == "35.000 TL"


def test_units_and_signature_cleanup():
    blocks = [{"type": "table", "rows": [["Güç", "1.850,5 MW MW"]]}, {"type": "signature"}, {"type": "para", "text": "x"}]
    out = doc_polish.polish(blocks, "rapor hazırla")
    assert out[0]["rows"][0][1] == "1.850,5 MW"
    assert all(b["type"] != "signature" for b in out)


def test_absurd_amount_and_stale_year_are_penalised():
    table = {"type": "table", "headers": ["Kalem", "Tutar"], "rows": [["Makine", "1,38 TL"], ["Mobilya", "125.000"], ["Mutfak", "35.000 TL"]]}
    spec = {"title": "t", "subtitle": "", "blocks": [table, {"type": "para", "text": "Tarih: 2019"}] * 2}
    _, issues = deliverable_score.score_document(spec, "plan")
    assert any("gerçekçi olmayan tutar" in i for i in issues)
    assert any("eski tarih" in i for i in issues)


def test_absurd_payback_is_flagged_and_repeated_tables_dropped():
    import doc_sanity

    table = {"type": "table", "headers": ["Kalem", "Değer", "Tür"], "rows": [["Geri Ödeme Süresi (Yıl)", "1.624.427,98", "hesaplanan"]]}
    assert doc_sanity.implausible_results({"blocks": [table]})
    assert len(doc_polish.polish([table, dict(table)], "rapor")) == 1


def test_table_columns_are_uniform_and_chart_follows_table():
    table = {"type": "table", "headers": ["Kalem", "Tutar (TL)", "Pay %"], "rows": [["A", "125000 TL", "50"], ["B", "35.500,5 TL", "30"], ["C", "9000 TL", "20"]]}
    chart = {"type": "chart", "title": "", "labels": ["a", "b", "c"], "values": [1, 2, 3]}
    blocks = [table, chart]
    doc_polish.polish(blocks, "rapor")
    assert table["rows"][0][1] == "125.000,0" and table["rows"][1][1] == "35.500,5"
    assert table["rows"][2][1] == "9.000,0"
    assert chart["values"][:2] == [125000.0, 35500.5]


def test_shares_not_adding_to_100_are_reported():
    import doc_tables

    table = {"type": "table", "headers": ["Kalem", "Pay %"], "rows": [["A", "50"], ["B", "30"], ["C", "5"]]}
    assert any("%100" in i for i in doc_tables.issues({"blocks": [table]}))


def test_unfillable_blank_sentences_are_dropped_but_identity_blanks_stay():
    blank = doc_polish.BLANK
    blocks = [
        {"type": "para", "text": f"Rapor hazırlandı. Hedef memnuniyet oranı %{blank} olacaktır. Sonuç olumludur."},
        {"type": "table", "headers": ["Kalem", "Değer"], "rows": [["A", "10"], ["B", blank], ["C", "30"]]},
        {"type": "para", "text": f"Müşteri Adı Soyadı: {blank}"},
    ]
    out = doc_polish.polish(blocks, "rapor hazırla")
    assert blank not in out[0]["text"] and "Sonuç olumludur" in out[0]["text"]
    assert len(out[1]["rows"]) == 2
    assert blank in out[2]["text"]
    assert doc_polish.polish([{"type": "para", "text": f"Tarih: {blank}"}], "toplantı tutanağı şablonu")[0]["text"].endswith(blank)


def test_urls_with_underscores_are_not_code_leaks():
    spec = {"title": "t", "subtitle": "", "blocks": [{"type": "bullets", "items": ["Kaynak — https://site.gov.tr/meb_iys_dosyalar/x_y"] * 3}, {"type": "para", "text": "Metin"}] * 2}
    assert not any("değişken adı" in i for i in deliverable_score.score_document(spec, "rapor")[1])
