"""A requested day/night switch that the generated page lacks is added; pages that have one are left alone."""

from __future__ import annotations

import pytest

import workspace_kit as kit

pytestmark = pytest.mark.unit


def test_toggle_is_added_when_asked_and_missing(tmp_path):
    (tmp_path / "index.html").write_text("<html><head></head><body><h1>Klinik</h1></body></html>", encoding="utf-8")
    assert kit.ensure_theme_toggle(tmp_path, "gece/gündüz modu düğmesi olsun")
    assert "theme-toggle" in (tmp_path / "index.html").read_text(encoding="utf-8")


def test_existing_toggle_or_no_request_changes_nothing(tmp_path):
    page = tmp_path / "index.html"
    page.write_text('<html><body><button id="dark-btn">Karanlık mod</button></body></html>', encoding="utf-8")
    assert not kit.ensure_theme_toggle(tmp_path, "gece/gündüz modu olsun")
    page.write_text("<html><body></body></html>", encoding="utf-8")
    assert not kit.ensure_theme_toggle(tmp_path, "basit bir site yap")
