"""Document maths is done in code: safe formulas, Turkish number format, placeholders."""

from __future__ import annotations

import pytest

import doc_calc
import doc_spec

pytestmark = pytest.mark.unit

CALC = {"inputs": [{"key": "a", "label": "A", "value": 120, "unit": "adet", "source": "user"}, {"key": "b", "label": "B", "value": 85, "unit": "TL"}],
        "outputs": [{"key": "c", "label": "C", "expr": "a*b*30", "unit": "TL"}, {"key": "bad", "expr": "__import__('os').system('x')"}, {"key": "div", "expr": "a/0"}]}


def test_formulas_are_exact_and_unsafe_ones_skipped():
    values, shown, _ = doc_calc.run(CALC)
    assert values["c"] == 306000 and shown["c"] == "306.000 TL"
    assert "bad" not in values and "div" not in values


def test_number_format_is_turkish():
    assert doc_calc.fmt_number(1234.5) == "1.234,5" and doc_calc.fmt_number(0.62) == "0,62" and doc_calc.fmt_number(5, "ay") == "5 ay"


def test_unknown_placeholder_never_invents_a_number():
    assert doc_calc.fill("Tutar {yok} ve {a}", {"a": "1"}) == "Tutar [................] ve 1"


def test_spec_resolves_text_tables_and_charts():
    spec = doc_spec.parse({"title": "T", "calc": CALC, "blocks": [
        {"type": "para", "text": "Aylık {c}"}, {"type": "calc_table"},
        {"type": "chart", "title": "x", "labels": ["A", "B"], "values": ["{c}", 5]}, {"type": "chart", "labels": ["A", "B"], "values": [-1, 2]}]})
    kinds = [b["type"] for b in spec["blocks"]]
    assert kinds == ["para", "table", "chart"] and spec["blocks"][0]["text"] == "Aylık 306.000 TL"


def test_unusable_spec_is_rejected():
    assert doc_spec.parse({"title": "T", "blocks": [{"type": "para", "text": "tek"}]}) is None
    assert doc_spec.parse({"blocks": []}) is None


def test_dates_the_user_never_wrote_become_blanks():
    raw = {"title": "T", "blocks": [{"type": "para", "text": "İmza tarihi 20.10.2023, başlangıç 01.01.2027."}, {"type": "bullets", "items": ["a"]}]}
    spec = doc_spec.parse(raw, "sözleşme hazırla, başlangıç 01.01.2027")
    assert "20.10.2023" not in spec["blocks"][0]["text"] and "01.01.2027" in spec["blocks"][0]["text"]


def test_turkish_placeholder_keys_resolve():
    _, shown, _ = doc_calc.run({"inputs": [{"key": "kira_tutarı", "label": "K", "value": 25000, "unit": "TL"}]})
    assert doc_calc.fill("Kira {kira_tutarı}", shown) == "Kira 25.000 TL"


def test_given_amounts_fill_blanks_and_table_fillers_go():
    raw = {"title": "T", "blocks": [
        {"type": "para", "text": "Aylık kira bedeli [................] TL'dir; depozito [................] ay kiradır."},
        {"type": "para", "text": "Finansal özet tablosu."}, {"type": "table", "headers": ["a", "b"], "rows": [["x", "y"]]}, {"type": "bullets", "items": ["k"]}]}
    spec = doc_spec.parse(raw, "kira 25.000 TL, depozito 2 aylık kira olsun")
    assert "25.000 TL'dir" in spec["blocks"][0]["text"] and "2 ay kiradır" in spec["blocks"][0]["text"]
    assert [b["type"] for b in spec["blocks"]] == ["para", "table", "bullets"]


def test_proofreading_edits_must_keep_numbers_and_blanks():
    import doc_proof

    old = "Aylık kira bedeli 25.000 TL'dir ve [................] hesaba yatırılır."
    assert doc_proof.acceptable(old, "Aylık kira bedeli 25.000 TL'dir; tutar [................] hesabına yatırılır.")
    assert not doc_proof.acceptable(old, "Aylık kira bedeli 30.000 TL'dir ve [................] hesaba yatırılır.")
    assert not doc_proof.acceptable(old, "Aylık kira bedeli 25.000 TL'dir ve hesaba yatırılır.")
    assert not doc_proof.acceptable(old, "Kısa.")


def test_missing_keys_are_found_with_their_sentence():
    draft = {"title": "T", "calc": {"inputs": [{"key": "a", "label": "A", "value": 2}], "outputs": []},
             "blocks": [{"type": "para", "text": "Aylık gelir {aylik_gelir} ve girdi {a}."}, {"type": "table", "headers": ["x", "y"], "rows": [["k", "{basabas}"]]}]}
    missing = doc_calc.missing_keys(draft)
    assert set(missing) == {"aylik_gelir", "basabas"} and "Aylık gelir" in missing["aylik_gelir"]


def test_deposit_is_computed_from_rent_and_months():
    raw = {"title": "T", "blocks": [{"type": "para", "text": "Kiracı depozito olarak [................] TL ödeyecektir."}, {"type": "bullets", "items": ["x"]}]}
    spec = doc_spec.parse(raw, "aylık kira 25.000 TL, depozito 2 aylık kira")
    assert "50.000 TL" in spec["blocks"][0]["text"]


def test_percentages_the_user_did_not_write_become_blanks():
    raw = {"title": "T", "calc": {"inputs": [{"key": "m", "label": "M", "value": 65, "unit": "%"}], "outputs": []},
           "blocks": [{"type": "para", "text": "Artış %50 olacak, KDV %20, marj {m}."}, {"type": "bullets", "items": ["x"]}]}
    text = doc_spec.parse(raw, "KDV %20 dahil bir plan")["blocks"][0]["text"]
    assert "%50" not in text and "%20" in text and "65 %" in text


def test_table_cells_are_flattened_and_formatted():
    raw = {"title": "T", "blocks": [{"type": "table", "headers": ["Kalem", "Tutar"], "rows": [["Yatırım", 850000.0], [["Gelir", 324600.0], ""], ["Not", "12.5"]]},
                                    {"type": "para", "text": "Metin"}, {"type": "bullets", "items": ["a"]}]}
    rows = doc_spec.parse(raw)["blocks"][0]["rows"]
    assert rows[0] == ["Yatırım", "850.000"] and rows[1][0] == "Gelir 324.600" and rows[2] == ["Not", "12,5"]
