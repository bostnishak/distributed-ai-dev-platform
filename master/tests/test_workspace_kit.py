"""The design kit is copied beside each page and linked after the model's own stylesheet."""

import pytest

from workspace_kit import inject_theme

pytestmark = pytest.mark.unit


def test_static_page_gets_kit_after_own_css(tmp_path):
    (tmp_path / "index.html").write_text('<html><head><link rel="stylesheet" href="css/styles.css"></head><body></body></html>', encoding="utf-8")
    assert inject_theme(tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert html.index("styles.css") < html.index("css/theme.css")
    assert (tmp_path / "css" / "theme.css").read_text(encoding="utf-8").startswith("/* Starter design kit")
    assert not inject_theme(tmp_path)  # idempotent


def test_flask_template_links_static_kit(tmp_path):
    (tmp_path / "backend" / "templates").mkdir(parents=True)
    (tmp_path / "backend" / "templates" / "index.html").write_text("<html><head></head><body></body></html>", encoding="utf-8")
    inject_theme(tmp_path)
    assert "/static/css/theme.css" in (tmp_path / "backend" / "templates" / "index.html").read_text(encoding="utf-8")
    assert (tmp_path / "backend" / "static" / "css" / "theme.css").exists()
