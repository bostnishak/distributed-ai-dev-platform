"""JSON answers get readable Turkish characters; non-JSON text and ASCII escapes are untouched."""

import json

import pytest

from stream_text import JsonUnescaper

pytestmark = pytest.mark.unit

BS = chr(92)  # a single backslash, so the test source needs no escape juggling


def _run(chunks):
    u = JsonUnescaper()
    return "".join(u.feed(c) for c in chunks) + u.flush()


def test_json_unicode_escapes_become_characters_even_when_split():
    out = _run(['[{"renk": "Sar', BS + "u", "0131", '"}, {"m": "' + BS + "u00c7il", 'ek"}]'])
    assert out == '[{"renk": "Sarı"}, {"m": "Çilek"}]'
    assert json.loads(out)[0]["renk"] == "Sarı"


def test_ascii_escapes_stay_valid_json():
    out = _run(['{"a": "q' + BS + "u0022uote" + BS + 'n"}'])
    assert json.loads(out)["a"] == 'q"uote\n'


def test_plain_text_and_code_untouched():
    text = "Python'da '" + BS + "u0131' yazılır"
    assert _run([text]) == text
    code = "```json\n" + '{"x": "' + BS + 'u0131"}'
    assert _run(["```json\n", '{"x": "' + BS + 'u0131"}']) == code
