"""Editor highlighting spans never reach a workspace file."""

import pytest

import workspace_batches

pytestmark = pytest.mark.unit


def test_highlighter_spans_are_removed():
    leaked = '<span class="hl-tag">&lt;p</span> <span class="hl-attr">id</span>=<span class="hl-str">"a"</span>'
    assert workspace_batches.pure_source(leaked) == '&lt;p id="a"'


def test_ordinary_spans_stay():
    page = '<span class="badge">3</span>'
    assert workspace_batches.pure_source(page) == page
