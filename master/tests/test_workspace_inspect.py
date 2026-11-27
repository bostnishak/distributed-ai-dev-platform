"""API console parsing, proof record and the default diff base."""

import pytest

import provenance
import workspace_inspect

pytestmark = pytest.mark.unit


def test_request_lines():
    parsed = workspace_inspect.parse_requests('GET /items\n\npost /items {"name": "kalem"}\n')
    assert [(r["method"], r["path"], r["json"]) for r in parsed] == [("GET", "/items", None), ("POST", "/items", {"name": "kalem"})]


@pytest.mark.parametrize(("text", "reason"), [("items", "1. satır"), ("GET /a\nPOST /b {x}", "2. satırdaki JSON"), ("", "istek yazın")])
def test_bad_lines_are_named(text, reason):
    with pytest.raises(ValueError, match=reason):
        workspace_inspect.parse_requests(text)


def test_proof_shows_changes_after_delivery(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace_inspect.wb, "list_snapshots", lambda _d: [{"version": "v1", "label": "ilk", "created_at": "2026-11-27T10:00:00", "files_count": 1}])
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    assert workspace_inspect.proof(tmp_path)["recorded"] is False
    provenance.write(tmp_path, "istek", ["bir uyarı"])
    clean = workspace_inspect.proof(tmp_path)
    assert clean["signed"] and clean["changed"] == [] and clean["warnings"] == ["bir uyarı"] and clean["timeline"][0]["version"] == "v1"
    (tmp_path / "app.py").write_text("x = 2\n", encoding="utf-8")
    assert workspace_inspect.proof(tmp_path)["changed"] == ["app.py"]
