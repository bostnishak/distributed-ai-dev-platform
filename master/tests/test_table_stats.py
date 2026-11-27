"""Exact table figures for uploaded files, including data-quality reporting."""

from __future__ import annotations

import pytest

import table_stats

pytestmark = pytest.mark.unit

TABLE = "Ürün | Adet | Fiyat\nElma | 10 | 5\nArmut | 3 | 8\nMuz | 7 | 12"
DIRTY = "Satıcı | Adet | Birim Fiyat\nAyşe | 2 | 25.000,50\nMehmet | 10 | 150\nAyşe |  | 450\nZeynep | 3 | -4000\nMehmet | 1 | 24.500,00\nZeynep | abc | 150"


def test_quantity_times_price_total_is_exact():
    out = table_stats.summary(TABLE)
    assert "toplam 158" in out and "Muz: 84" not in out and "en yüksek: Armut" not in out


def test_dirty_rows_are_reported_and_excluded():
    out = table_stats.summary(DIRTY)
    assert "toplam 76.001" in out and "satır 4 (Ayşe)" in out and "satır 7 (Zeynep" in out and "negatif" in out
    assert "Ayşe: 50.001" in out and "en yüksek: Ayşe" in out


def test_non_tabular_text_gets_no_summary():
    assert table_stats.summary("Bu bir paragraf.\nİkinci satır.") == ""


def test_text_columns_are_not_summed():
    assert "Ürün (geçerli" not in table_stats.summary(TABLE)
