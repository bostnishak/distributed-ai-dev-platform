"""Plan v3 verification tests: DOS-08 handwriting OCR, ALT-11 single venv, full FE<->BE contract wiring, and JS safety."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

import app as master_app
import contract_check
from rag.parsing import recognize_handwriting_image_bytes

REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_handwritten_png() -> bytes:
    img = Image.new("RGB", (320, 120), color=(250, 248, 240))
    draw = ImageDraw.Draw(img)
    # Draw dark handwritten-like strokes across two horizontal bands
    draw.line([(20, 35), (120, 32), (180, 40), (280, 34)], fill=(20, 20, 25), width=4)
    draw.line([(25, 80), (140, 76), (220, 84), (295, 78)], fill=(20, 20, 25), width=4)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_dos08_handwriting_ocr_preprocess_and_endpoint():
    """DOS-08: Handwriting OCR preprocesses ink strokes and works via POST /api/rag/ocr/handwriting."""
    png = _make_handwritten_png()
    res = recognize_handwriting_image_bytes(png, language="tur+eng")
    assert res["engine"] in {"trocr-local", "tesseract-handwriting", "preprocessed-offline"}
    assert res["preprocessed"]["width"] == 320
    assert res["preprocessed"]["height"] == 120
    assert res["preprocessed"]["ink_ratio"] > 0.0
    assert res["preprocessed"]["estimated_lines"] >= 2

    client = TestClient(master_app.app)
    resp = client.post(
        "/api/rag/ocr/handwriting",
        files={"file": ("notlar.png", png, "image/png")},
        data={"language": "tur+eng", "ingest": "false"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["filename"] == "notlar.png"
    assert body["preprocessed"]["estimated_lines"] >= 2

    bad = client.post(
        "/api/rag/ocr/handwriting",
        files={"file": ("bad.exe", b"MZ", "application/octet-stream")},
    )
    assert bad.status_code == 415


def test_alt11_single_master_venv_consistency():
    """ALT-11: Only master/venv exists; duplicate master/.venv is removed and config points to master/venv."""
    assert (REPO_ROOT / "master" / "venv").exists()
    assert not (REPO_ROOT / "master" / ".venv").exists()
    pyrefly = (REPO_ROOT / "pyrefly.toml").read_text(encoding="utf-8")
    assert 'master/venv/Scripts/python.exe' in pyrefly


def test_fe_be_contract_check_zero_disconnected_routes():
    """FE <-> BE: contract_check reports ok=True and 0 unwired backend /api/ routes."""
    report = contract_check.run_check(master_app.app)
    assert report["ok"] is True, f"Broken FE routes: {report['missing_in_backend']}"
    assert len(report["backend_routes"]) >= 230
    assert report["not_called_by_frontend"] == [], f"Unwired BE routes: {report['not_called_by_frontend']}"


def test_agh_and_jsd_runtime_safety_rules_zero():
    """AGH-01..30 & JSD-01..88: scan_js.py reports literally 0 findings across all master/static JS/CSS/HTML."""
    out_file = REPO_ROOT / ".pytest_scan_js_tmp.json"
    try:
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "audit" / "scan_js.py"), str(out_file)],
            check=True,
            capture_output=True,
            text=True,
        )
        rows = json.loads(out_file.read_text(encoding="utf-8"))
    finally:
        out_file.unlink(missing_ok=True)

    assert rows == [], f"Expected 0 scan_js findings, got: {rows[:10]}"


def test_ble001_zero_across_master():
    """BLE-01..94: Zero blind except Exception (BLE001) findings across production master/."""
    res = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "master", "--isolated", "--exclude", "master/tests", "--select", "BLE001,S110,S608,S607"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Ruff BLE001/S110/S608/S607 failed:\n{res.stdout}\n{res.stderr}"
