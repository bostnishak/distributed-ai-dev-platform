"""Tests for CNC Technical Drawing Ballooning Engine & API."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from docx import Document
from fastapi.testclient import TestClient
from openpyxl import Workbook

import app as app_mod
import cnc_ballooning as cnc
import config

pytestmark = pytest.mark.integration


def test_parse_cnc_dimensions():
    dia = cnc.parse_cnc_dimension("Ø42 H7")
    assert dia is not None
    assert dia.category == "Çap (Ø)"
    assert dia.nominal == 42.0
    assert dia.fit_class == "H7"
    assert dia.min_limit == 42.0
    assert dia.max_limit == 42.025
    assert dia.criticality == "Kritik"

    th = cnc.parse_cnc_dimension("4x M8x1.25-6H")
    assert th is not None
    assert th.category == "Diş / Vida"
    assert th.quantity == 4

    ra = cnc.parse_cnc_dimension("Ra 0.8")
    assert ra is not None
    assert ra.category == "Yüzey Pürüzlülüğü"
    assert ra.nominal == 0.8
    assert ra.criticality == "Kritik"

    gdt = cnc.parse_cnc_dimension("⊥ 0.03 A")
    assert gdt is not None
    assert gdt.category == "GD&T"
    assert gdt.nominal == 0.03

    ch = cnc.parse_cnc_dimension("2x45°")
    assert ch is not None
    assert ch.category == "Pah (Chamfer)"

    # Non-dimensions should be ignored
    assert cnc.parse_cnc_dimension("SCALE: 1:1") is None
    assert cnc.parse_cnc_dimension("MATERIAL: AISI 4140") is None


def test_cnc_demo_and_exports(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "CNC_JOBS_DIR", tmp_path / "cnc_jobs")
    client = TestClient(app_mod.app)

    resp = client.post("/api/cnc/demo")
    assert resp.status_code == 200
    job = resp.json()
    assert job["id"] == "demo-flange-fln2026"
    assert len(job["balloons"]) >= 12
    assert job["metadata"]["part_number"] == "FLN-2026-042"

    # All 4 export formats + original must download cleanly
    for kind in ("original", "ballooned.png", "ballooned.pdf", "report.xlsx", "report.docx"):
        dl = client.get(f"/api/cnc/jobs/{job['id']}/file/{kind}")
        assert dl.status_code == 200
        assert len(dl.content) > 500

    # Edit balloons & re-render
    edited = job["balloons"][:5]
    put = client.put(f"/api/cnc/jobs/{job['id']}/balloons", json={"balloons": edited})
    assert put.status_code == 200
    assert len(put.json()["balloons"]) == 5


def test_cnc_docx_and_xlsx_upload(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "CNC_JOBS_DIR", tmp_path / "cnc_jobs")
    client = TestClient(app_mod.app)

    # DOCX with dimensions
    doc = Document()
    doc.add_paragraph("PART NO: SHAFT-01")
    doc.add_paragraph("Ø42 H7")
    doc.add_paragraph("Ra 1.6")
    doc.add_paragraph("M10x1.5-6H")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    r_docx = client.post(
        "/api/cnc/balloon",
        files={"file": ("shaft_spec.docx", buf.read(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert r_docx.status_code == 200
    assert len(r_docx.json()["balloons"]) == 3

    # XLSX with dimensions
    wb = Workbook()
    ws = wb.active
    ws.append(["PART NO: PLATE-99", "Ø25 ±0.02", "2x45°", "⊥ 0.02 A"])
    xbuf = io.BytesIO()
    wb.save(xbuf)
    xbuf.seek(0)

    r_xlsx = client.post(
        "/api/cnc/balloon",
        files={"file": ("plate_dims.xlsx", xbuf.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r_xlsx.status_code == 200
    assert len(r_xlsx.json()["balloons"]) == 3


def test_cnc_dxf_cad_upload_and_cost_gcode(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "CNC_JOBS_DIR", tmp_path / "cnc_jobs")
    client = TestClient(app_mod.app)

    # Minimal valid ASCII DXF with LINE, CIRCLE, and TEXT dimensions
    dxf_content = "\n".join([
        "0", "SECTION", "2", "ENTITIES",
        "0", "CIRCLE", "10", "100.0", "20", "100.0", "40", "55.0",
        "0", "LINE", "10", "45.0", "20", "100.0", "11", "155.0", "21", "100.0",
        "0", "TEXT", "10", "90.0", "20", "160.0", "1", "%%c110 %%p0.05",
        "0", "TEXT", "10", "95.0", "20", "100.0", "1", "%%c42 H7",
        "0", "TEXT", "10", "140.0", "20", "80.0", "1", "4x M8x1.25-6H",
        "0", "TEXT", "10", "60.0", "20", "50.0", "1", "Ra 0.8",
        "0", "TEXT", "10", "10.0", "20", "15.0", "1", "PART NO: DXF-900",
        "0", "TEXT", "10", "10.0", "20", "10.0", "1", "MATERIAL: AISI 4140",
        "0", "ENDSEC", "0", "EOF",
    ])

    resp = client.post(
        "/api/cnc/balloon",
        files={"file": ("flange_cad.dxf", dxf_content.encode("utf-8"), "application/dxf")},
    )
    assert resp.status_code == 200
    job = resp.json()
    assert job["engine_used"] == "dxf-cad-vector+iso2768"
    assert len(job["balloons"]) == 4
    plan = job["manufacturing_plan"]
    assert plan["cost_estimate"]["unit_quote_1_tl"] > 0
    assert plan["cost_estimate"]["cycle_time_min"] > 0
    assert "O2026" in plan["gcode_template"]
    assert "G84" in plan["gcode_template"]
