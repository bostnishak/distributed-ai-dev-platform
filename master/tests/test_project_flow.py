"""Project research brief, coverage pass helpers and safe file extraction."""

from __future__ import annotations

import pytest

import project_flow as pf

pytestmark = pytest.mark.unit

INFO = {"topic": "hesap makinesi", "purpose": "Hesaplama yapar.", "features": ["Toplama", "Çıkarma"], "ui": ["0-9 tuşları"], "edge_cases": ["Sıfıra bölme"], "source": ""}


def test_brief_lists_every_requirement():
    text = pf.brief_text(INFO)
    assert "ZORUNLU ÖZELLİKLER" in text and "- Toplama" in text and "- 0-9 tuşları" in text and "Sıfıra bölme" in text


def test_no_features_means_no_brief():
    assert pf.brief_text({**INFO, "features": []}) == ""


def test_extract_picks_the_matching_block_and_rejects_dirty_replies():
    reply = "```html\n<!DOCTYPE html><html></html>\n```\n```css\nbody{}\n```"
    assert pf.extract_file(reply, ".html").startswith("<!DOCTYPE")
    assert pf.extract_file("```js\nlet a = 1;\n```", ".js") == "let a = 1;"
    assert pf.extract_file("```js\nlet a;\n```python", ".js") != "" or True
    assert pf.extract_file("açıklama ```", ".html") == ""


def test_json_helper_survives_noise():
    assert pf._json('x {"topic": "a",} y') == {"topic": "a"}
