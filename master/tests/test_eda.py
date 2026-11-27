"""The table report and model are measured: real signal is found, noise and leakage are called out."""

import random

import pytest

import eda

pytestmark = pytest.mark.unit


def _table(signal: bool, leak: bool = False, rows: int = 200):
    rng = random.Random(1)
    lines = ["id,saat,sicaklik,gurultu,satis" + (",satis_kopya" if leak else "")]
    for i in range(rows):
        hour, heat, noise = rng.randint(0, 23), rng.randint(5, 35), rng.randint(0, 1000)
        sales = hour * 10 + heat * 3 + rng.randint(-5, 5) if signal else rng.randint(0, 500)
        lines.append(f"{i},{hour},{heat},{noise},{sales}" + (f",{sales}" if leak else ""))
    return "\n".join(lines) + "\n"


def test_real_signal_is_found_and_ids_are_dropped():
    pytest.importorskip("sklearn")
    text = eda.report(_table(True), "satis için tahmin modeli kur")
    score = float(text.split("R²")[1].split("**")[1])
    assert score > 0.9 and "saat" in text.split("En etkili sütunlar:")[1].split("\n")[0] and "çıkarıldı: id" in text


def test_noise_is_not_sold_as_a_model():
    pytest.importorskip("sklearn")
    assert "anlamlı ölçüde iyi değil" in eda.report(_table(False), "satis tahmin et")


def test_a_leaking_column_is_reported_not_used():
    pytest.importorskip("sklearn")
    text = eda.report(_table(True, leak=True), "predict satis")
    assert "UYARI (sızıntı): satis_kopya" in text


def test_too_few_rows_and_missing_target():
    pytest.importorskip("sklearn")
    assert "en az 30" in " ".join(eda.model_report(eda.rows_of(_table(True, rows=12)), "satis"))
    assert "Hangi sütunun" in eda.report(_table(True), "tahmin modeli kur")


def test_profile_without_a_model_request():
    text = eda.report("sehir,adet\nAnkara,3\nİzmir,\nBursa,900\n", "veri analizi yap")
    assert "3 satır" in text and "adet: 1" in text and "Tahmin modeli" not in text
