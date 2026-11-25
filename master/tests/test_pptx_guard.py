"""Deck outlines: statistics survive only when the request supports them; slides keep their content; length is capped."""

import pytest

from pptx_guard import clean_spec

pytestmark = pytest.mark.unit


def _spec():
    return {"slides": [
        {"title": "A", "layout": "bullets", "bullets": ["Çalışanların %81'i risk altında", "Eğitim önemlidir"], "key_fact": "%90 artış"},
        {"title": "B", "layout": "kpi_grid", "kpis": [{"value": "%65", "label": "Önleme"}, {"value": "%81", "label": "Risk"}], "bullets": []},
        {"title": "C", "layout": "closing", "bullets": ["Sürekli eğitim verin"]},
    ]}


def test_invented_numbers_removed_without_source_numbers():
    out = clean_spec(_spec(), "siber güvenlik sunumu", 6)["slides"]
    assert out[0]["bullets"] == ["Eğitim önemlidir"] and out[0]["key_fact"] == ""
    assert [x["title"] for x in out] == ["A", "C"]  # a KPI-only slide has nothing left to say without its numbers


def test_numbers_the_user_gave_are_kept():
    out = clean_spec(_spec(), "Çalışanların %81'i risk altında, önleme %65, artış %90 olan bir sunum", 6)["slides"]
    assert "%81" in out[0]["bullets"][0] and out[1]["layout"] == "kpi_grid" and out[0]["key_fact"] == "%90 artış"


def test_other_numbers_in_the_request_do_not_license_invented_ones():
    out = clean_spec(_spec(), "Q1 %12 büyüme ile sunum", 6)["slides"]
    assert out[0]["bullets"] == ["Eğitim önemlidir"]


def test_numbers_derived_from_the_request_are_kept():
    spec = {"slides": [{"title": "M", "layout": "bullets", "bullets": ["Birim marj 209 TL", "Yıllık ciro 4.188.000 TL", "Pazar payı hedefi %7,3 olur"]}]}
    out = clean_spec(spec, "fiyat 349 TL, maliyet 140 TL, 12.000 adet satış, pazar 85 milyon TL", 5)["slides"][0]["bullets"]
    assert out[:2] == ["Birim marj 209 TL", "Yıllık ciro 4.188.000 TL"] and "%7,3" not in " ".join(out)


def test_chart_values_must_come_from_the_request():
    chart = {"title": "Satış", "labels": ["2026", "2027"], "values": [12000, 30000], "unit": "adet"}
    spec = {"slides": [{"title": "G", "layout": "chart", "chart": chart, "bullets": ["a", "b", "c"]}]}
    assert clean_spec(spec, "2026: 12.000 adet, 2027: 30.000 adet", 5)["slides"][0]["layout"] == "chart"
    assert clean_spec(spec, "satış grafiği olsun", 5)["slides"][0]["layout"] == "bullets"


def test_slide_count_capped_keeping_closing():
    out = clean_spec(_spec(), "x 1", 2)["slides"]
    assert [s["title"] for s in out] == ["A", "C"]


def test_slide_count_phrase_is_not_source_data():
    out = clean_spec(_spec(), "6 slaytlık siber güvenlik sunumu", 6)["slides"]
    assert out[0]["bullets"] == ["Eğitim önemlidir"]
    out = clean_spec(_spec(), "Create a 6-slide deck", 6)["slides"]
    assert out[0]["bullets"] == ["Eğitim önemlidir"]


def test_invented_percentages_are_removed_from_tables_and_thin_slides_are_padded():
    spec = {"slides": [
        {"layout": "kpi_grid", "title": "T", "kpis": [{"value": "%5", "label": "Tıklama"}], "bullets": ["a"], "notes": "Birinci cümle burada yeterince uzun yazıldı. İkinci cümle de yeterince uzun yazıldı."},
        {"layout": "table", "title": "U", "table": {"headers": ["a"], "rows": [["%90 Oranında Yüksek"]]}, "bullets": ["b", "c", "d"]}]}
    out = clean_spec(spec, "siber güvenlik", 3)["slides"]
    assert out[0]["layout"] == "bullets" and len(out[0]["bullets"]) >= 3 and out[0]["kicker"] == "ÖNEMLİ NOKTALAR"
    assert out[1]["table"]["rows"] == [["Yüksek"]]


def test_notes_with_invented_statistics_are_cleaned():
    spec = {"slides": [{"title": "N", "layout": "bullets", "bullets": ["a", "b", "c"], "notes": "Güvenli cümle burada. Saldırıların %70'i e-posta ile gelir."}]}
    assert "%70" not in clean_spec(spec, "siber", 5)["slides"][0]["notes"]


def test_kpi_card_stays_when_only_its_delta_is_invented():
    spec = {"slides": [{"title": "K", "layout": "kpi_grid", "kpis": [{"value": "349 TL", "label": "Fiyat", "delta": "+%15"}, {"value": "140 TL", "label": "Maliyet", "delta": ""}], "bullets": ["a", "b", "c"]}]}
    kpis = clean_spec(spec, "fiyat 349 TL, maliyet 140 TL", 5)["slides"][0]["kpis"]
    assert [k["delta"] for k in kpis] == ["", ""] and [k["value"] for k in kpis] == ["349 TL", "140 TL"]


def test_chart_values_in_thousands_are_accepted():
    chart = {"labels": ["2026", "2027", "2028"], "values": [12, 30, 65], "unit": "bin adet"}
    spec = {"slides": [{"title": "G", "layout": "chart", "chart": chart, "bullets": ["a", "b", "c"]}]}
    assert clean_spec(spec, "2026: 12.000, 2027: 30.000, 2028: 65.000 adet", 5)["slides"][0]["layout"] == "chart"


def test_wrong_multiplication_claims_are_removed():
    spec = {"slides": [{"title": "M", "layout": "bullets", "bullets": ["Satış üç katına çıkacak", "İkinci madde güvenli", "Üçüncü madde güvenli"]}]}
    out = clean_spec(spec, "2026: 12.000 adet, 2027: 30.000 adet", 5)["slides"][0]["bullets"]
    assert out == ["İkinci madde güvenli", "Üçüncü madde güvenli"]
    assert "2,5 kat" in clean_spec({"slides": [{"title": "M", "layout": "bullets", "bullets": ["Satış 2,5 kat artar", "x", "y"]}]}, "2026: 12.000 adet, 2027: 30.000 adet", 5)["slides"][0]["bullets"][0]


def test_wrongly_rounded_figures_and_all_dash_rows_are_removed():
    table = {"headers": ["Kriter", "2026", "2028"], "rows": [["Satış", "12.000 adet", "65.000 adet"], ["Ciro", "4,18 Milyon TL", "22,63 Milyon TL"], ["Pazar payı", "%5", "%15"]]}
    spec = {"slides": [{"title": "T", "layout": "table", "table": table, "bullets": ["a", "b", "c"]}]}
    rows = clean_spec(spec, "fiyat 349 TL, 12.000 adet, 65.000 adet", 5)["slides"][0]["table"]["rows"]
    assert rows == [["Satış", "12.000 adet", "65.000 adet"], ["Ciro", "4,18 Milyon TL", "—"]]
