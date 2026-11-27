"""Repo map, blast radius and resuming an interrupted build."""

import asyncio

import pytest

import checkpoint
import repo_map

pytestmark = pytest.mark.unit


def _project(root):
    files = {
        "db.py": "def connect(path):\n    return path\n",
        "service.py": "from db import connect\n\n\ndef load_orders():\n    return connect('x')\n",
        "app.py": "from service import load_orders\n\n\ndef main():\n    return load_orders()\n",
        "lonely.py": "def unused():\n    return 1\n",
    }
    for name, text in files.items():
        (root / name).write_text("\n".join(text.split("\n")), encoding="utf-8")


def test_most_used_file_comes_first_and_requested_file_jumps_ahead(tmp_path):
    _project(tmp_path)
    plain = repo_map.build(tmp_path, "bir şey değiştir")
    assert plain.index("db.py") < plain.index("lonely.py")
    focused = repo_map.build(tmp_path, "lonely.py içindeki fonksiyonu düzelt")
    assert focused.index("lonely.py") < focused.index("db.py")
    assert "connect(path)" in plain


def test_budget_keeps_other_files_by_name(tmp_path):
    _project(tmp_path)
    small = repo_map.build(tmp_path, "", budget=90)
    assert "yalnız ad" in small and len(small) < 400


def test_blast_radius_is_transitive(tmp_path):
    _project(tmp_path)
    note = repo_map.dependents_note(tmp_path, ["db.py"])
    assert "service.py" in note and "app.py" in note and "lonely.py" not in note


@pytest.mark.parametrize(("text", "resumes"), [
    ("devam et", True), ("Kaldığın yerden devam et.", True), ("devam", True),
    ("devam eden siparişleri listeleyen bir uygulama yap", False), ("butonu mavi yap", False),
])
def test_resume_phrases(text, resumes):
    assert bool(checkpoint._RESUME_RE.match(text)) == resumes


def test_resume_writes_only_the_missing_files(tmp_path, monkeypatch):
    import workspace_builder as wb
    import workspace_smoke

    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "db.py").write_text("def connect():\n    return 1\n", encoding="utf-8")
    checkpoint.save(ws, "sipariş uygulaması", "m", [{"path": "db.py", "purpose": "veri"}, {"path": "app.py", "purpose": "giriş"}])
    checkpoint.done(ws, "db.py")
    written = []

    async def write(ws_dir, model, spec, prompt):
        written.append(spec["path"])
        (ws_dir / spec["path"]).write_text("def main():\n    return 0\n", encoding="utf-8")
        return "def main():\n    return 0\n"

    async def smoke(*_):
        yield {"type": "warning", "warning": ""}

    async def pick(*_):
        return "m"

    monkeypatch.setattr(wb, "safe_workspace_dir", lambda _id: ws)
    monkeypatch.setattr(wb, "load_workspace_meta", lambda _d: {"id": "ws", "name": "x", "project_type": "python"})
    monkeypatch.setattr(wb, "save_workspace_meta", lambda *_: None)
    monkeypatch.setattr(wb, "create_snapshot", lambda *_: None)
    monkeypatch.setattr(wb, "list_snapshots", lambda _d: [])
    monkeypatch.setattr(wb, "pick_coder_model", pick)
    monkeypatch.setattr(wb, "_generate_and_write_file", write)
    monkeypatch.setattr(workspace_smoke, "smoke_and_repair", smoke)

    async def collect():
        return [e async for e in checkpoint.stream_resume("ws")]

    events = asyncio.run(collect())
    assert written == ["app.py"] and events[-1]["type"] == "done"
    assert checkpoint.load(ws) is None
