"""Colour codes and quoted labels of a request must be present in the generated page."""

import pytest

import spec_contract

pytestmark = pytest.mark.unit
_REQUEST = 'Arka plan #0F172A, buton #3B82F6. Üstte "Aktif Görev: X" ve "Tümünü Temizle" butonu.'


def test_extracts_colours_and_fixed_label_text():
    assert spec_contract.extract(_REQUEST) == {"colors": ["#0F172A", "#3B82F6"], "labels": ["Aktif Görev", "Tümünü Temizle"], "sizes": []}


def test_missing_items_are_reported_until_present(tmp_path):
    page = tmp_path / "index.html"
    page.write_text("<style>body{background:#0f172a}</style><p>Aktif Görev: 3</p><button>Temizle</button>", encoding="utf-8")
    found = spec_contract.problem(tmp_path, _REQUEST)
    assert found is not None and "#3B82F6" in found[1] and "Tümünü Temizle" in found[1] and "#0F172A" not in found[1]
    page.write_text("<style>a{color:#3B82F6;background:#0F172A}</style>Aktif Görev: 0 <button>Tümünü Temizle</button>", encoding="utf-8")
    assert spec_contract.problem(tmp_path, _REQUEST) is None and (tmp_path / ".spec.json").is_file()


def test_plain_requests_are_not_checked(tmp_path):
    (tmp_path / "index.html").write_text("<p>x</p>", encoding="utf-8")
    assert spec_contract.problem(tmp_path, "bir hesap makinesi yap") is None
