"""v5 milestone 12: the README may not drift from the code, and the exported ZIP carries a working start kit."""

from __future__ import annotations

import io
import zipfile

import pytest

import doc_drift
import portable_kit

pytestmark = pytest.mark.unit

APP = '''import sqlite3

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/api/notlar")
def liste():
    with sqlite3.connect("notlar.db") as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS notlar (metin TEXT)")
        return [row[0] for row in conn.execute("SELECT metin FROM notlar")]


@app.post("/api/notlar", status_code=201)
def ekle(metin: str):
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def sayfa():
    return "<!doctype html><meta charset='utf-8'><title>Notlar</title><h1>Notlar hazır</h1>"
'''
CLI = 'import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument("--dosya")\nparser.parse_args()\n'
GOOD_README = """# Notlar
Çalıştırma: `uvicorn app:app --port 8000`, sonra http://127.0.0.1:8000 adresini aç.
Dosyalar: `app.py`, `araclar.py`. Veritabanı `app.db` ilk çalıştırmada oluşur.
Uç noktalar: GET /api/notlar ve POST /api/notlar
Araç: `python araclar.py --dosya notlar.txt`
"""
BAD_README = GOOD_README + """Ayrıca `eski_modul.py` içinde ayarlar var.
Silmek için DELETE /api/notlar/{id}
Sunucu http://localhost:9999 adresindedir.
`python araclar.py --hizli`
`python yok.py`
Alternatif: `uvicorn main:app`
"""


def _project(root, readme):
    (root / "app.py").write_text(APP, encoding="utf-8")
    (root / "araclar.py").write_text(CLI, encoding="utf-8")
    (root / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")
    (root / "README.md").write_text(readme, encoding="utf-8")
    return root


def test_accurate_readme_passes(tmp_path):
    assert doc_drift.check(_project(tmp_path, GOOD_README)) == []


def test_each_kind_of_drift_is_found_and_blocks_delivery(tmp_path):
    import done_gate

    found = " | ".join(doc_drift.lines(_project(tmp_path, BAD_README)))
    for word in ("eski_modul.py", "DELETE /api/notlar/{id}", "port: 9999", "--hizli", "olmayan betik: yok.py", "uvicorn hedefi yok: main:app"):
        assert word in found, f"{word} bulunamadı: {found}"
    status, detail = done_gate.live_proof(tmp_path, [])
    assert status == done_gate.FAILED and "README" in detail


def test_repair_leaves_only_true_statements(tmp_path):
    _project(tmp_path, BAD_README)
    changed = doc_drift.repair(tmp_path)
    text = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "6 satır" in changed[0] and doc_drift.check(tmp_path) == []
    assert "- GET `/api/notlar`" in text and "uvicorn app:app --port 8000" in text and "9999" not in text
    assert doc_drift.repair(tmp_path) == []


def test_export_zip_carries_a_pinned_start_kit_without_touching_the_project(tmp_path):
    (tmp_path / "notlar").mkdir()
    ws = _project(tmp_path / "notlar", GOOD_README)
    data = portable_kit.archive(ws, "notlar")
    names = set(zipfile.ZipFile(io.BytesIO(data)).namelist())
    for wanted in ("run.ps1", "run_windows.bat", "start_app.py", "requirements.lock", "Dockerfile", "docker-compose.yml", ".dockerignore", "app.py"):
        assert f"notlar/{wanted}" in names, wanted
    archive = zipfile.ZipFile(io.BytesIO(data))
    lock = archive.read("notlar/requirements.lock").decode()
    assert "fastapi==" in lock and "uvicorn" in lock
    assert archive.read("notlar/run.ps1").startswith(b"\xef\xbb\xbf"), "Windows PowerShell Türkçe için BOM ister"
    assert b"\r\n" in archive.read("notlar/run_windows.bat")
    compile(archive.read("notlar/start_app.py"), "start_app.py", "exec")
    docker = archive.read("notlar/Dockerfile").decode()
    assert "USER app" in docker and "uvicorn app:app --host 0.0.0.0 --port 8000" in docker and "WORKDIR /data" in docker
    assert "data:/data" in archive.read("notlar/docker-compose.yml").decode()
    assert not (ws / "run.ps1").exists() and not (ws / "requirements.lock").exists()


def test_static_page_and_existing_files_are_respected(tmp_path):
    (tmp_path / "index.html").write_text("<p>merhaba</p>", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM benim\n", encoding="utf-8")
    made = portable_kit.files(tmp_path)
    assert portable_kit.detect(tmp_path).kind == "sayfa" and "Dockerfile" not in made and "requirements.lock" not in made
    assert b"http.server" in made["start_app.py"]
    (tmp_path / "bos").mkdir()
    assert portable_kit.files(tmp_path / "bos") == {} and portable_kit.docker_test(tmp_path / "bos")[0] is False


def test_exported_app_that_writes_beside_itself_runs_in_the_container_and_keeps_its_data(tmp_path):
    """The failure the live proof found: "unable to open database file" at start-up."""
    import workspace_docker

    if not workspace_docker.available():
        pytest.skip("Docker yok")
    (tmp_path / "app.py").write_text(APP + "\n\nsqlite3.connect('acilista.db').execute('CREATE TABLE IF NOT EXISTS t (a)')\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")
    passed, detail = portable_kit.docker_test(tmp_path)
    assert passed, detail
