"""A page that links a stylesheet by the wrong relative path gets the link repaired (or the shared theme written)."""

from __future__ import annotations

import pytest

import workspace_requirements as wr

pytestmark = pytest.mark.unit


def test_link_is_pointed_at_the_existing_file(tmp_path):
    (tmp_path / "css").mkdir()
    (tmp_path / "css" / "theme.css").write_text("body{}", encoding="utf-8")
    page = tmp_path / "index.html"
    page.write_text('<link rel="stylesheet" href="theme.css"><script src="js/app.js"></script>', encoding="utf-8")
    wr._fix_missing_local_refs(tmp_path)
    assert 'href="css/theme.css"' in page.read_text(encoding="utf-8")


def test_missing_theme_is_written_from_the_kit(tmp_path):
    page = tmp_path / "index.html"
    page.write_text('<link rel="stylesheet" href="theme.css">', encoding="utf-8")
    wr._fix_missing_local_refs(tmp_path)
    assert (tmp_path / "theme.css").is_file()
