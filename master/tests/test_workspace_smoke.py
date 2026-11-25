"""Generated projects are run once; a crash is sent back to the model for repair."""

import asyncio

import pytest

from workspace_smoke import smoke_and_repair

pytestmark = pytest.mark.unit


async def _collect(ws, regen):
    return [e async for e in smoke_and_repair(ws, regen)]


def test_broken_entry_is_repaired(tmp_path):
    (tmp_path / "main.py").write_text("import json\nvalue = undefined_name\n", encoding="utf-8")
    calls = []

    async def regen(path, ask):
        calls.append((path, ask))
        return "```python\nvalue = 1\n```"

    events = asyncio.run(_collect(tmp_path, regen))
    assert events[-1]["ok"] is True and calls and calls[0][0] == "main.py" and "undefined_name" in calls[0][1]


def test_unfixable_project_reports_a_warning(tmp_path):
    (tmp_path / "main.py").write_text("raise ValueError('kaputt')\n", encoding="utf-8")

    async def regen(path, ask):
        return ""

    last = asyncio.run(_collect(tmp_path, regen))[-1]
    assert last["ok"] is False and "kaputt" in last["warning"]


def test_project_without_entry_is_skipped(tmp_path):
    async def regen(path, ask):
        raise AssertionError

    assert asyncio.run(_collect(tmp_path, regen))[-1]["ok"] is True


def test_static_web_project_with_wrong_id_is_repaired(tmp_path):
    (tmp_path / "index.html").write_text('<html><head></head><body><ul id="list"></ul><script src="app.js"></script></body></html>', encoding="utf-8")
    (tmp_path / "app.js").write_text("document.getElementById('taskList').innerHTML = '';", encoding="utf-8")

    async def regen(path, ask):
        assert path == "app.js"
        return "document.getElementById('list').innerHTML = '';"

    events = asyncio.run(_collect(tmp_path, regen))
    assert events[-1]["ok"] is True
