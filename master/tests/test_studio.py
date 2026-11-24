"""Tests for AI Project Studio / Workspace Builder API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as app_mod
import config
import workspace_builder as wb

pytestmark = pytest.mark.integration


def test_workspace_tree_file_crud_and_preview(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACES_DIR", tmp_path / "workspaces")
    ws_dir = wb.safe_workspace_dir("demo-shop")
    ws_dir.mkdir(parents=True, exist_ok=True)
    wb.save_workspace_meta(ws_dir, {
        "id": "demo-shop",
        "name": "Demo Shop",
        "project_type": "web",
        "entry_point": "index.html",
    })
    (ws_dir / "index.html").write_text("<h1>Merhaba CNC</h1>", encoding="utf-8")
    (ws_dir / "css").mkdir()
    (ws_dir / "css" / "app.css").write_text("body { color: red; }", encoding="utf-8")

    client = TestClient(app_mod.app)

    # List workspaces
    r_list = client.get("/api/studio/workspaces")
    assert r_list.status_code == 200
    assert len(r_list.json()["workspaces"]) == 1
    assert r_list.json()["workspaces"][0]["has_web_preview"] is True

    # Tree structure
    r_tree = client.get("/api/studio/workspaces/demo-shop/tree")
    assert r_tree.status_code == 200
    tree = r_tree.json()["tree"]
    names = [n["name"] for n in tree]
    assert "css" in names and "index.html" in names

    # Read & save file
    r_read = client.get("/api/studio/workspaces/demo-shop/file", params={"path": "css/app.css"})
    assert r_read.status_code == 200
    assert "color: red" in r_read.json()["content"]

    r_put = client.put("/api/studio/workspaces/demo-shop/file", json={"path": "js/main.js", "content": "console.log(1);"})
    assert r_put.status_code == 200

    # Path traversal blocked
    r_bad = client.get("/api/studio/workspaces/demo-shop/file", params={"path": "../../secret.txt"})
    assert r_bad.status_code == 400

    # Live preview serves HTML
    r_prev = client.get("/api/studio/workspaces/demo-shop/preview/index.html")
    assert r_prev.status_code == 200
    assert "Merhaba CNC" in r_prev.text

    # Download ZIP
    r_zip = client.get("/api/studio/workspaces/demo-shop/download.zip")
    assert r_zip.status_code == 200
    assert r_zip.headers["content-type"] == "application/zip"
    assert len(r_zip.content) > 100

    # Delete file
    r_del = client.delete("/api/studio/workspaces/demo-shop/file", params={"path": "js/main.js"})
    assert r_del.status_code == 200


def test_workspace_snapshots_rollback_and_zip_import(tmp_path: Path, monkeypatch):
    import io
    import zipfile

    import company_rag

    monkeypatch.setattr(config, "WORKSPACES_DIR", tmp_path / "workspaces")
    client = TestClient(app_mod.app)

    # 1. Create a ZIP in-memory and import it into a workspace
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("my-app/index.html", "<h1>Surum 1</h1>")
        zf.writestr("my-app/css/style.css", "body { background: #111; }")
    meta, tree = wb.import_zip_workspace("my-app.zip", zbuf.getvalue())
    ws_id = meta["id"]
    assert meta["has_web_preview"] is True
    assert len(tree) == 2

    # 2. Modify index.html and create v2 snapshot
    ws_dir = wb.safe_workspace_dir(ws_id)
    (ws_dir / "index.html").write_text("<h1>Surum 2</h1>", encoding="utf-8")
    wb.create_snapshot(ws_dir, "Baslik guncellendi")

    r_hist = client.get(f"/api/studio/workspaces/{ws_id}/history")
    assert r_hist.status_code == 200
    versions = [v["version"] for v in r_hist.json()["versions"]]
    assert "v1" in versions and "v2" in versions

    # 3. Rollback to v1
    r_rest = client.post(f"/api/studio/workspaces/{ws_id}/restore/v1")
    assert r_rest.status_code == 200
    assert (ws_dir / "index.html").read_text(encoding="utf-8") == "<h1>Surum 1</h1>"

    # 4. Company RAG Knowledge Base search
    docs = company_rag.search_company_kb_sync("Ø42 H7 geçme toleransı ve M8 kılavuz ön delik çapı nedir?")
    assert len(docs) >= 1
    assert any("H7" in d["content"] or "6.8" in d["content"] for d in docs)
