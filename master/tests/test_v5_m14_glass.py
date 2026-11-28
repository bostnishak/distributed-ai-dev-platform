"""v5 milestone 14: hardware ribbon data, proof drawer, screenshots, one-click undo and unfinished builds."""

from __future__ import annotations

import json
import time

import pytest
from fastapi import HTTPException

import checkpoint
import config
import filmstrip
import glass_box
import workspace_builder as wb

pytestmark = pytest.mark.integration


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACES_DIR", tmp_path / "workspaces")
    ws_dir = wb.safe_workspace_dir("notlar-1")
    (ws_dir / "css").mkdir(parents=True)
    (ws_dir / "index.html").write_text("<!doctype html><p>ilk</p>", encoding="utf-8")
    (ws_dir / "css" / "a.css").write_text("p{}", encoding="utf-8")
    wb.save_workspace_meta(ws_dir, {"id": "notlar-1", "name": "Notlar", "project_type": "web"})
    return ws_dir


def test_one_click_takes_the_last_change_back_quickly(project):
    glass_box.snapshot_before(project, "başlığı değiştir")
    (project / "index.html").write_text("<p>ikinci</p>", encoding="utf-8")
    (project / "yeni.js").write_text("1", encoding="utf-8")
    wb.create_snapshot(project, "başlığı değiştir")
    started = time.perf_counter()
    result = glass_box.undo("notlar-1")
    assert time.perf_counter() - started < 1.0 and result["undone"] == "başlığı değiştir"
    assert (project / "index.html").read_text(encoding="utf-8") == "<!doctype html><p>ilk</p>" and not (project / "yeni.js").exists()
    with pytest.raises(HTTPException) as nothing:
        glass_box.undo("notlar-1")
    assert nothing.value.status_code == 409


def test_proof_drawer_shows_marks_preview_and_screenshots(project):
    (project / ".ai-os" / "filmstrip").mkdir(parents=True)
    (project / ".ai-os" / "filmstrip" / "1-ilk-acilis.png").write_bytes(b"\x89PNG")
    (project / ".ai-os" / "proof.json").write_text(json.dumps({"proofs": {"C": ["kaldı", "konsol hatası"], "A": ["geçti", "temiz"]}}), encoding="utf-8")
    data = glass_box.proof("notlar-1")
    assert [(m["name"].split(" ")[0], m["state"]) for m in data["marks"]] == [("Statik", "geçti"), ("Canlı", "kaldı")]
    assert data["preview"].endswith("/notlar-1/preview/index.html") and data["film"] == ["1-ilk-acilis.png"]
    assert glass_box.film("notlar-1", "1-ilk-acilis.png").path.name == "1-ilk-acilis.png"
    for name in ("../proof.json", "..%2f.png", "yok.png"):
        with pytest.raises(HTTPException):
            glass_box.film("notlar-1", name)
    with pytest.raises(HTTPException):
        glass_box.proof("../..")


def test_unfinished_builds_are_listed(project):
    assert glass_box.unfinished() == {"unfinished": []}
    checkpoint.save(project, "not uygulaması yap", "m", [{"path": "index.html"}, {"path": "js/app.js"}])
    checkpoint.done(project, "index.html")
    found = glass_box.unfinished()["unfinished"]
    assert found == [{"id": "notlar-1", "name": "Notlar", "done": 1, "total": 2, "request": "not uygulaması yap"}]


def test_hardware_ribbon_reports_real_machine_values():
    data = glass_box.hardware()
    assert 0 < data["ram_used_gb"] <= data["ram_total_gb"] and 0 <= data["cpu_percent"] <= 100
    assert data["isolation"].startswith("Yalıtım") and isinstance(data["models"], list)


def test_film_of_a_real_page_has_the_user_journey(tmp_path):
    (tmp_path / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'><input id='n'><button id='b'>Ekle</button><ul id='l'></ul>"
        "<script>b.onclick = () => { if (!n.value.trim()) return; const i = document.createElement('li'); i.textContent = n.value; l.append(i); };</script>",
        encoding="utf-8",
    )
    made = filmstrip.capture((tmp_path / "index.html").as_uri(), tmp_path)
    if not made:
        pytest.skip("tarayıcı yok")
    assert made == ["1-ilk-acilis.png", "2-dolu-form.png", "3-gonderim-sonrasi.png", "4-yenileme-sonrasi.png", "5-bos-girdi.png"]
    assert all((tmp_path / filmstrip.FOLDER / name).stat().st_size > 1000 for name in made)


def test_new_routes_require_a_local_or_admin_caller():
    from access_control import require_local_or_admin

    for route in glass_box.router.routes:
        assert any(d.dependency is require_local_or_admin for d in route.dependencies), route.path
