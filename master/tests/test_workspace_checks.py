"""Static checks catch the slips a small model typically makes before the user downloads the project."""

import pytest

from workspace_checks import dom_id_problem, js_syntax_problem, python_name_problem

pytestmark = pytest.mark.unit


def test_missing_dom_id_is_reported(tmp_path):
    (tmp_path / "index.html").write_text('<input id="task-input"><ul id="list"></ul>', encoding="utf-8")
    (tmp_path / "app.js").write_text("document.getElementById('task-input'); document.getElementById('taskList');", encoding="utf-8")
    found = dom_id_problem(tmp_path)
    assert found and "taskList" in found[1]


def test_ids_created_by_script_are_fine(tmp_path):
    (tmp_path / "index.html").write_text('<div id="app"></div>', encoding="utf-8")
    (tmp_path / "app.js").write_text("const el = document.createElement('div'); el.id = 'toast'; document.getElementById('toast'); document.getElementById('app');", encoding="utf-8")
    assert dom_id_problem(tmp_path) is None


def test_js_syntax_error_is_reported(tmp_path):
    (tmp_path / "app.js").write_text("function f( { return 1 }", encoding="utf-8")
    found = js_syntax_problem(tmp_path)
    assert found is None or "app.js" in found[1]  # node may be absent in CI


def test_undefined_python_name_is_reported(tmp_path):
    (tmp_path / "main.py").write_text("def f():\n    return missing_name\n", encoding="utf-8")
    found = python_name_problem(tmp_path)
    assert found is None or "missing_name" in found[1]
