"""Lenient JSON loading for model output."""

from __future__ import annotations

import pytest

from json_repair import loads_top

pytestmark = pytest.mark.unit


def test_plain_and_fenced():
    assert loads_top('metin {"a": 1} son') == {"a": 1}
    assert loads_top('```json\n{"a": [1, 2]}\n```') == {"a": [1, 2]}


def test_trailing_commas_and_raw_newlines_in_strings():
    assert loads_top('{"a": [1, 2,], "t": "iki\nsatır",}') == {"a": [1, 2], "t": "iki\nsatır"}


def test_truncated_output_is_closed():
    got = loads_top('{"title": "T", "blocks": [{"type": "para", "text": "uzun met')
    assert got["title"] == "T" and got["blocks"][0]["type"] == "para"


def test_outer_object_wins_over_inner_ones():
    got = loads_top('{"calc": {"x": 1}, "blocks": [{"type": "para"} ,]}')
    assert "blocks" in got and got["calc"] == {"x": 1}


def test_garbage_is_none():
    assert loads_top("no json here") is None and loads_top("") is None
