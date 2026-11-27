"""Security scan, run traces and model-free edits."""

import asyncio

import pytest

import config
import run_trace
import security_scan
import tier0_edit

pytestmark = pytest.mark.unit


def test_scan_finds_secrets_and_unsafe_calls(tmp_path):
    (tmp_path / "app.py").write_text('API_KEY = "abcd1234efgh5678"\ncur.execute(f"SELECT * FROM t WHERE id={i}")\n', encoding="utf-8")
    (tmp_path / "app.js").write_text("box.innerHTML = userText;\neval(code);\n", encoding="utf-8")
    found = security_scan.scan(tmp_path)
    assert {f["line"] for f in found if f["file"] == "app.py"} == {1, 2}
    assert len(found) == 4 and security_scan.report(tmp_path).startswith("Güvenlik taraması 4 bulgu")


def test_clean_code_has_no_findings(tmp_path):
    (tmp_path / "app.js").write_text("el.textContent = name;\ncur.execute('SELECT 1')\nel.innerHTML = '';\n", encoding="utf-8")
    assert security_scan.report(tmp_path) == ""


def test_secrets_are_redacted():
    assert "abcd1234efgh" not in security_scan.redact('password = "abcd1234efgh"')


def test_trace_records_stages_and_verdict(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "x.db")

    async def events():
        yield {"type": "status", "message": "plan"}
        yield {"type": "done", "workspace": {"id": "w1"}, "warnings": []}

    async def drain():
        return [e async for e in run_trace.traced(events(), "istek")]

    assert len(asyncio.run(drain())) == 2
    summary = run_trace.summary()
    assert summary["runs"] == 1 and summary["pass_rate"] == 1.0


def test_exact_replacements_need_no_model(tmp_path):
    page = tmp_path / "index.html"
    page.write_text('<style>b{color:#F2AA4C}</style><button>Not Ekle</button>', encoding="utf-8")
    assert tier0_edit.apply(tmp_path, "#f2aa4c yerine #10B981 yap") == ["index.html"]
    assert tier0_edit.apply(tmp_path, '"Not Ekle" yazısını "Kaydet" yap') == ["index.html"]
    assert "#10B981" in page.read_text(encoding="utf-8") and "Kaydet" in page.read_text(encoding="utf-8")


def test_vague_requests_go_to_the_model(tmp_path):
    (tmp_path / "index.html").write_text("<p>x</p>", encoding="utf-8")
    assert tier0_edit.apply(tmp_path, "butonu yeşil yap") == []


def test_primary_button_colour_changes_the_css_variable(tmp_path):
    page = tmp_path / "index.html"
    page.write_text("<style>:root{--btn-primary: #F2AA4C; --bg: #101820}</style>", encoding="utf-8")
    assert tier0_edit.apply(tmp_path, "Ana buton rengini yeşil #10B981 yap.") == ["index.html"]
    assert page.read_text(encoding="utf-8") == "<style>:root{--btn-primary: #10B981; --bg: #101820}</style>"


def test_process_descriptions_are_not_refused_as_drawings():
    import flowchart_studio

    assert flowchart_studio.is_flow_request("Şu süreç için akış şeması çiz: sipariş alınır, kargoya verilir.")
