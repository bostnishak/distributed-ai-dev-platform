"""Functional page check: which results count as a problem and which file gets repaired (jsdom itself is not started here)."""

from __future__ import annotations

import pytest

import workspace_web as ww

pytestmark = pytest.mark.unit


def _site(tmp_path):
    (tmp_path / "js").mkdir()
    (tmp_path / "js" / "app.js").write_text("x", encoding="utf-8")
    (tmp_path / "index.html").write_text('<script src="js/app.js"></script>', encoding="utf-8")
    return tmp_path


def test_script_errors_point_at_the_failing_file(tmp_path):
    d = _site(tmp_path)
    target, text = ww.problem(d, {"errors": ["TypeError: x at file:///sandbox/js/app.js:12:3"], "controls": 5, "changed": True})
    assert target == d / "js" / "app.js" and "TypeError" in text


def test_broken_values_on_screen_are_a_problem(tmp_path):
    d = _site(tmp_path)
    assert ww.problem(d, {"errors": [], "controls": 5, "changed": True, "texts": ["Hesap NaN 7 8"]})
    assert ww.problem(d, {"errors": [], "controls": 5, "changed": True, "texts": ["Bir nullable alan"]}) is None


def test_dead_controls_are_a_problem_but_a_static_page_is_not(tmp_path):
    d = _site(tmp_path)
    assert ww.problem(d, {"errors": [], "controls": 6, "changed": False, "texts": ["a"]})
    assert ww.problem(d, {"errors": [], "controls": 1, "changed": False, "texts": ["a"]}) is None
