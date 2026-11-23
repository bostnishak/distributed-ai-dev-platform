"""Tests for Universal Bidirectional File Converter, ZIP Pack/Extract, and External MCP Connector."""

from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as master_app
import document_factory as df
import file_converter as fc
import mcp_connector as mcpc


def test_bidirectional_pdf_docx_pptx_and_zip_roundtrip(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("config.DATA_DIR", tmp_path)

    # Create a sample Turkish PDF first
    src_pdf = tmp_path / "ornek_rapor.pdf"
    df._build_pdf(
        src_pdf,
        "İnsanlık Tarihi Raporu",
        "Türkçe karakter testi: ğüşiöçİĞÜŞÖÇ",
        [{"heading": "1. Antik Çağ", "content": "Sümerler yazıyı icat etti. Şehir devletleri kuruldu."}],
        ["Dönem", "Yıl"],
        [["Antik", "-3500"]],
    )
    pdf_bytes = src_pdf.read_bytes()

    # 1. PDF -> DOCX
    assert fc.detect_conversion_or_archive_action("bu pdf dosyasını docx'e çevir", "ornek_rapor.pdf") == {
        "action": "convert",
        "target_fmt": "docx",
    }
    res_docx = fc.convert_uploaded_file("ornek_rapor.pdf", pdf_bytes, "docx")
    assert res_docx["output_path"].is_file() and res_docx["size_kb"] > 10

    # 2. PDF -> PPTX
    res_pptx = fc.convert_uploaded_file("ornek_rapor.pdf", pdf_bytes, "pptx")
    assert res_pptx["output_path"].is_file()
    with zipfile.ZipFile(res_pptx["output_path"]) as zf:
        assert "ppt/slideMasters/slideMaster1.xml" in zf.namelist()

    # 3. DOCX -> PDF
    docx_bytes = res_docx["output_path"].read_bytes()
    res_pdf2 = fc.convert_uploaded_file("ornek.docx", docx_bytes, "pdf")
    assert res_pdf2["output_path"].is_file() and res_pdf2["output_path"].read_bytes().startswith(b"%PDF")

    # 4. PPTX -> DOCX
    pptx_bytes = res_pptx["output_path"].read_bytes()
    res_docx2 = fc.convert_uploaded_file("sunum.pptx", pptx_bytes, "docx")
    assert res_docx2["output_path"].is_file()

    # 5. Pack into named folder + ZIP, then Extract ZIP
    assert fc.detect_conversion_or_archive_action("bunu klasöre al ziple", "ornek_rapor.pdf") == {"action": "pack_zip"}
    zres = fc.pack_files_to_folder_zip("ornek_rapor.pdf", [("ornek_rapor.pdf", pdf_bytes)])
    zip_path = tmp_path / "media" / zres["zip_filename"]
    assert zip_path.is_file()
    assert zres["included_files"] == ["ornek_rapor/ornek_rapor.pdf"]

    assert fc.detect_conversion_or_archive_action("bu zipi aç içini çıkar", zres["zip_filename"]) == {
        "action": "extract_zip"
    }
    ext_res = fc.extract_zip_to_media(zres["zip_filename"], zip_path.read_bytes())
    assert ext_res["file_count"] == 1
    assert ext_res["files"][0]["url"].startswith("/api/assistant/media/")

    # 6. Zip project detection
    assert fc.detect_conversion_or_archive_action("son projeyi ziple", None) == {"action": "zip_project"}


def test_mcp_connector_crud_and_key_masking(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("config.DB_PATH", tmp_path / "test_mcp.db")
    mcpc.init_mcp_db()

    client = TestClient(master_app.app)
    r_create = client.post(
        "/api/mcp/connectors",
        json={
            "name": "GitHub MCP",
            "url": "https://mcp.example.com/rpc",
            "api_key": "ghp_supersecretkey1234567890",
            "auth_header": "Authorization",
            "auth_prefix": "Bearer ",
            "description": "Harici GitHub MCP",
        },
    )
    assert r_create.status_code == 200
    conn = r_create.json()["connector"]
    cid = conn["id"]
    assert conn["has_api_key"] is True
    assert "supersecret" not in conn["api_key_masked"]
    assert conn["api_key_masked"] == "ghp_...7890"

    r_list = client.get("/api/mcp/connectors")
    assert r_list.status_code == 200
    assert any(c["id"] == cid for c in r_list.json()["connectors"])

    r_upd = client.put(f"/api/mcp/connectors/{cid}", json={"enabled": False})
    assert r_upd.status_code == 200
    assert r_upd.json()["connector"]["enabled"] is False

    r_del = client.delete(f"/api/mcp/connectors/{cid}")
    assert r_del.status_code == 200
    assert r_del.json()["deleted"] is True

    _ = tempfile.gettempdir()
