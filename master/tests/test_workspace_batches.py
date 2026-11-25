"""Project files are generated anchor-first, independent files in pairs, tests last."""

from __future__ import annotations

import pytest

from workspace_batches import file_batches

pytestmark = pytest.mark.unit


def _files(*names):
    return [{"path": n, "purpose": n} for n in names]


def test_anchor_first_pairs_then_tests_last():
    batches = file_batches(_files("index.html", "style.css", "app.js", "data.js", "tests/test_app.py"))
    assert [[f["path"] for f in b] for b in batches] == [["index.html"], ["style.css", "app.js"], ["data.js"], ["tests/test_app.py"]]


def test_one_by_one_when_disabled(monkeypatch):
    monkeypatch.setenv("WS_PARALLEL", "1")
    assert all(len(b) == 1 for b in file_batches(_files("a.html", "b.css", "c.js")))
