"""UX-11 artifact versions and UX-12 real file upload."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app as master_app
from orchestrator.state import apply_targeted_edit, list_artifact_versions, save_artifact

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    return TestClient(master_app.app)


def _artifact():
    return save_artifact(kind="document", title="rapor", sections=["bir", "iki", "uc"], user_id="ux-test", chat_id="c1")


def test_edit_keeps_every_earlier_version(client):
    art = _artifact()
    aid = art["artifact_id"]
    apply_targeted_edit(aid, 1, "iki-v2")
    apply_targeted_edit(aid, 1, "iki-v3")
    versions = list_artifact_versions(aid)
    assert [v["version"] for v in versions] == [2, 1]
    assert versions[-1]["sections"] == ["bir", "iki", "uc"]
    r = client.get(f"/api/orchestrator/artifacts/{aid}/versions")
    assert r.status_code == 200 and len(r.json()["versions"]) == 2
    assert client.get("/api/orchestrator/artifacts/yok/versions").status_code == 404


def test_upload_indexes_a_text_file_and_rejects_bad_ones(client):
    ok = client.post(
        "/api/rag/ingest-file",
        files={"file": ("notlar.md", "# Başlık\n\nTürkiye'nin başkenti Ankara'dır.".encode(), "text/markdown")},
        data={"collection_id": "ux-test", "user_id": "ux-test"},
    )
    assert ok.status_code == 200, ok.text
    bad = client.post("/api/rag/ingest-file", files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert bad.status_code == 415
    empty = client.post("/api/rag/ingest-file", files={"file": ("bos.txt", b"", "text/plain")})
    assert empty.status_code == 400


def test_listing_a_collection_that_does_not_exist_is_empty_not_forbidden(client):
    r = client.get("/api/rag/collections/never-created/documents?user_id=ux-test")
    assert r.status_code == 200 and r.json() == {"documents": []}
