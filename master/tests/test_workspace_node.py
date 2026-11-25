"""Node project detection and error-frame mapping (the container is not started here)."""

from __future__ import annotations

import pytest

import workspace_node

pytestmark = pytest.mark.unit


def test_entry_from_start_script(tmp_path):
    (tmp_path / "package.json").write_text('{"scripts": {"start": "node api/main.js"}}', encoding="utf-8")
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "main.js").write_text("1", encoding="utf-8")
    assert workspace_node.find_entry(tmp_path) == "api/main.js"


def test_no_package_json_is_not_a_node_project(tmp_path):
    (tmp_path / "server.js").write_text("1", encoding="utf-8")
    assert workspace_node.find_entry(tmp_path) is None


def test_fallback_entry(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "x"}', encoding="utf-8")
    (tmp_path / "index.js").write_text("1", encoding="utf-8")
    assert workspace_node.find_entry(tmp_path) == "index.js"


def test_failing_file_maps_container_path(tmp_path):
    (tmp_path / "bad.js").write_text("1", encoding="utf-8")
    log = "Require stack:\n- /sandbox/bad.js\n    at Object.<anonymous> (/sandbox/bad.js:1:17)"
    assert workspace_node.failing_file(tmp_path, log) == tmp_path / "bad.js"
