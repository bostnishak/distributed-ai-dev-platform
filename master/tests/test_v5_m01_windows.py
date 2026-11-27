"""v5 milestone 01: ports, child processes, locked and long files, Turkish letters, GPU, databases, disk."""

import asyncio
import os
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import closing

import pytest

import atomic_io
import db_health
import disk_gc
import eda
import gpu_watch
import os_kernel
import process_registry
import turkish
from gateway import priority_gate

pytestmark = pytest.mark.unit


@pytest.fixture
def data(tmp_path, monkeypatch):
    import config

    folder = tmp_path / "data"
    folder.mkdir()
    monkeypatch.setattr(config, "data_dir", lambda: folder)
    monkeypatch.setattr(config, "DB_PATH", folder / "platform.db")
    return folder


def test_a_port_in_use_or_already_leased_is_never_handed_out():
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        busy = taken.getsockname()[1]
        assert not process_registry.free_port(busy)
    first = process_registry.lease_port()
    second = process_registry.lease_port()
    assert first != second and first in process_registry.PORTS
    process_registry.release_port(first)
    process_registry.release_port(second)


def _sleeper():
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])


def test_tracked_child_is_ended_and_forgotten(data):
    child = _sleeper()
    process_registry.track(child, "deneme", memory_mb=512)
    assert [e["pid"] for e in process_registry.listing()] == [child.pid]
    process_registry.untrack(child.pid)
    assert child.wait(timeout=10) is not None and process_registry.listing() == []


def test_orphans_of_a_dead_server_are_reaped_but_a_reused_pid_is_left_alone(data):
    orphan, innocent = _sleeper(), _sleeper()
    born = process_registry._identity(orphan.pid)
    process_registry._save([
        {"pid": orphan.pid, "born": born, "owner": 999_999, "owner_born": 1.0, "purpose": "eski sunucu", "port": 0},
        {"pid": innocent.pid, "born": 1.0, "owner": 999_999, "owner_born": 1.0, "purpose": "pid yeniden kullanılmış", "port": 0},
    ])
    try:
        assert process_registry.reap() == [f"eski sunucu (pid {orphan.pid})"]
        assert orphan.wait(timeout=10) is not None and innocent.poll() is None
    finally:
        innocent.kill()


def test_atomic_write_waits_out_a_lock_and_keeps_utf8_lf(tmp_path, monkeypatch):
    target = tmp_path / "şğü İ.txt"
    real, failures = os.replace, {"left": 3}

    def locked(src, dst):
        if failures["left"]:
            failures["left"] -= 1
            raise PermissionError(32, "başka bir süreç kullanıyor")
        real(src, dst)

    monkeypatch.setattr(os, "replace", locked)
    atomic_io.write_text(target, "İstanbul\r\nığdır\n")
    assert target.read_bytes() == "İstanbul\nığdır\n".encode() and not list(tmp_path.glob("*.tmp"))
    failures["left"] = 99
    monkeypatch.setattr(atomic_io.time, "sleep", lambda _s: None)
    with pytest.raises(PermissionError):
        atomic_io.write_text(target, "yeni")
    assert atomic_io.read_text(target) == "İstanbul\nığdır\n" and not list(tmp_path.glob("*.tmp"))


def test_paths_beyond_the_classic_limit_work_and_can_be_removed(tmp_path):
    deep = tmp_path / "kök"
    for i in range(12):
        deep = deep / f"çok-uzun-klasör-adı-{i:02d}"
    target = deep / "dosya.txt"
    assert len(str(target)) > 260
    atomic_io.write_text(target, "tamam")
    assert atomic_io.read_text(target) == "tamam"
    os.chmod(atomic_io.long_path(target), 0o444)
    atomic_io.remove_tree(tmp_path / "kök")
    assert not (tmp_path / "kök").exists()


def test_turkish_letters_and_order():
    assert turkish.lower("IĞDIR İSTANBUL") == "ığdır istanbul" and turkish.upper("ığdır istanbul") == "IĞDIR İSTANBUL"
    assert sorted(["İzmir", "Isparta", "Çorum", "Ceyhan", "Şile", "Siirt"], key=turkish.sort_key) == ["Ceyhan", "Çorum", "Isparta", "İzmir", "Siirt", "Şile"]
    assert turkish.matches("istanbul", "Büyük İSTANBUL ili") and eda.target_of("il bazında dağılım", ["İl", "Adet"]) == "İl"


def test_hot_card_or_low_battery_holds_only_background_work(monkeypatch):
    monkeypatch.setattr(gpu_watch, "on_low_battery", lambda: False)
    heat = {"t": 84}
    monkeypatch.setattr(gpu_watch, "read", lambda: gpu_watch.Reading(heat["t"], 6000, 8188, "test"))
    gpu_watch._CACHE["holding"] = False
    assert "84 °C" in gpu_watch.hold_reason()
    heat["t"] = 80
    assert gpu_watch.hold_reason()  # still cooling down
    heat["t"] = 77
    assert gpu_watch.hold_reason() == ""
    assert gpu_watch.context_budget(16384) == 4096 and gpu_watch.context_budget(16384, loaded_mb=5000) == 16384

    waited = []

    async def fake_wait():
        waited.append(1)

    monkeypatch.setattr(priority_gate, "_wait_until_safe", fake_wait)

    async def run():
        gate = priority_gate.PriorityGate(1)
        async with gate.slot("chat"):
            pass
        async with gate.slot("self_eval"):
            pass

    asyncio.run(run())
    assert waited == [1]


def test_broken_database_is_reported_and_backup_is_consistent_under_writes(data):
    good = data / "platform.db"
    with closing(sqlite3.connect(good)) as conn, conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE t (v INTEGER)")
    (data / "bozuk.db").write_bytes(b"SQLite format 3\x00" + b"\x07" * 4000)
    stop = threading.Event()

    def writer():
        with closing(sqlite3.connect(good, timeout=10)) as conn:
            while not stop.is_set():
                conn.execute("INSERT INTO t VALUES (1)")
                conn.commit()

    thread = threading.Thread(target=writer)
    thread.start()
    time.sleep(0.2)
    broken = db_health.startup_check()
    copy = db_health.hot_backup(good, "test")
    stop.set()
    thread.join()
    assert list(broken) == ["bozuk.db"] and db_health.quick_check(copy) == "ok"
    assert list((data / "backups" / "db").glob("platform-boot-*.db"))
    for _ in range(8):
        db_health.hot_backup(good, "many")
    assert len(list((data / "backups" / "db").glob("platform-many-*.db"))) == 5
    assert db_health.flush() >= 1


def test_disk_cleanup_shows_first_and_never_offers_projects(data, monkeypatch):
    monkeypatch.setattr(disk_gc.tempfile, "gettempdir", lambda: str(data.parent / "tmp"))
    old = time.time() - 90 * 86400
    for rel in ("media/eski.png", "media/yeni.png", "runs/a.jsonl", "workspaces/proje/index.html", "platform.db"):
        path = data / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * 100)
        if "yeni" not in rel:
            os.utime(path, (old, old))
    shown = disk_gc.answer("disk temizle")
    assert "henüz hiçbir şey silinmedi" in shown and (data / "media" / "eski.png").exists()
    assert "Silindi: 2 öğe" in disk_gc.answer("disk temizle uygula")
    assert (data / "media" / "yeni.png").exists() and (data / "workspaces" / "proje" / "index.html").exists() and (data / "platform.db").exists()
    assert "boş" in disk_gc.answer("disk durumu") and disk_gc.answer("disk nedir?") == ""


def test_sleep_is_noticed_and_status_answers(data):
    assert os_kernel.woke_from_sleep(600) and not os_kernel.woke_from_sleep(16)
    text = os_kernel.answer("sistem durumu")
    assert "Disk:" in text and "Çalışan alt süreç: 0" in text


def test_a_foreign_program_on_the_preview_port_never_receives_previews(monkeypatch):
    import preview_server

    with socket.socket() as foreign:
        foreign.bind(("127.0.0.1", 0))
        foreign.listen()
        taken = foreign.getsockname()[1]
        monkeypatch.setattr(preview_server.config, "PREVIEW_PORT", taken)
        monkeypatch.setattr(preview_server, "_STATE", {"port": 0})
        monkeypatch.setattr(preview_server, "_is_preview", lambda port: False)
        started = []
        monkeypatch.setattr(preview_server.threading.Thread, "start", lambda self: started.append(self.name))
        preview_server.start_preview_server_background()
        chosen = int(preview_server.get_preview_origin().rsplit(":", 1)[1])
        assert chosen != taken and started == ["preview-origin-server"]
        process_registry.release_port(chosen)


def test_computed_figures_are_written_the_turkish_way():
    import table_stats

    assert table_stats._fmt(3104) == "3.104" and table_stats._fmt(2345.5) == "2.345,5" and table_stats._fmt(7) == "7"


def test_a_heavy_design_request_is_not_mistaken_for_small_talk():
    import complexity_governor

    assert complexity_governor.classify("Ödeme entegrasyonlu, mikroservis mimarili bir ERP tasarla ve güvenliğini doğrula").level == 3
    assert complexity_governor.classify("Ödeme nedir?").level == 0


def test_the_patch_request_does_not_also_ask_for_the_whole_file():
    import patch_edit

    seen = []

    async def generate(_system, user):
        seen.append(user)
        return "<<<<<<< SEARCH\n<p>0</p>\n=======\n<p>sıfır</p>\n>>>>>>> REPLACE"

    current = "\n".join(f"<p>{i}</p>" for i in range(300))
    patched = asyncio.run(patch_edit.try_patch(generate, "değiştir\nBu dosyanın güncel ve EKSİKSİZ tüm içeriğini yaz.", current))
    assert patched.startswith("<p>sıfır</p>") and "EKSİKSİZ" not in seen[0] and "tamamını YAZMA" in seen[0]


def test_plan_matrix_maps_every_requirement_and_flags_a_missing_endpoint(tmp_path):
    import plan_matrix

    (tmp_path / "app.py").write_text("@app.get('/api/x')\ndef x():\n    return []\n\n@app.post(\"/api/x\", status_code=201)\ndef y():\n    return {}\n", encoding="utf-8")
    contract = {"colors": ["#112233"], "labels": ["Ekle"], "buttons": [{"label": "Ekle", "behavior": "kaydeder"}], "persistence": "kayıtlar",
                "endpoints": [{"method": "GET", "path": "/api/x"}, {"method": "DELETE", "path": "/api/x/{id}"}]}
    warnings = plan_matrix.write(tmp_path, contract, ["app.py"])
    plan = __import__("json").loads((tmp_path / ".ai-os" / "plan.json").read_text(encoding="utf-8"))
    assert [r["id"] for r in plan["acceptance"]][:2] == ["REQ-001", "REQ-002"] and len(plan["acceptance"]) == 6
    assert plan["endpoints"][1] == {"method": "POST", "path": "/api/x", "status": 201, "file": "app.py"}
    assert warnings == ["Sözleşme: DELETE /api/x/{id} EKSİK: kodda tanımlı değil"]


def test_intake_keeps_only_what_the_user_said_and_empty_handlers_are_found(tmp_path):
    import agent_contracts
    import shortcut_audit

    async def chat(_system, _user, _schema, _ctx):
        return __import__("json").dumps({"endpoints": [{"method": "GET", "path": "/api/kitap"}, {"method": "GET", "path": "/uydurma"}], "persistence": "kitaplar", "regions": ["yan menü", "uzay paneli"]})

    spec = asyncio.run(agent_contracts.intake("Yan menü olsun, GET /api/kitap ucu olsun.", chat))
    assert [e.path for e in spec.endpoints] == ["/api/kitap"] and spec.persistence == "" and spec.regions == ["yan menü"]
    (tmp_path / "a.js").write_text("b.addEventListener('click', () => {})\nc.onclick = function () { }\nd.onclick = () => save()\n", encoding="utf-8")
    (tmp_path / "a.html").write_text('<button onclick="">x</button>', encoding="utf-8")
    assert sum("boş olay işleyicisi" in f for f in shortcut_audit.findings(tmp_path)) == 3


def test_a_file_with_highlighter_markup_cannot_be_saved(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import app as app_module
    import config
    import workspace_builder as wb

    monkeypatch.setattr(config, "WORKSPACES_DIR", tmp_path)
    (tmp_path / "p1").mkdir()
    client = TestClient(app_module.app)
    bad = client.put("/api/studio/workspaces/p1/file", json={"path": "a.html", "content": '<span class="hl-tag">&lt;p&gt;</span>'})
    good = client.put("/api/studio/workspaces/p1/file", json={"path": "a.html", "content": '<span class="highlight">p</span>'})
    assert bad.status_code == 400 and good.status_code == 200 and wb.safe_workspace_dir("p1").joinpath("a.html").exists()


def test_narrow_screen_keyboard_and_hurried_clicks_are_checked(tmp_path):
    pytest.importorskip("playwright")
    import ui_chaos

    page = tmp_path / "index.html"
    page.write_text("<meta charset='utf-8'><div style='width:900px'>geniş</div><div onclick='this.textContent=1'>tıkla</div>"
                    "<form onsubmit='event.preventDefault(); l.innerHTML += \"<li>\" + m.value + \"</li>\"'><input id=m><button>Ekle</button></form><ul id=l></ul>", encoding="utf-8")
    found = ui_chaos.ergonomics(page)
    if found is None:
        pytest.skip("tarayıcı yok")
    text = " | ".join(found)
    assert "320 px" in text and "klavyeyle" in text and "boşlukla" in text and "çift tıklama" in text, text
    page.write_text("<meta charset='utf-8'><meta name=viewport content='width=device-width'><form onsubmit='event.preventDefault(); const b=this.querySelector(\"button\"); if(!m.value.trim()||b.disabled) return; b.disabled=true; l.innerHTML+=\"<li>\"+m.value+\"</li>\"'><input id=m style='width:90%'><button>Ekle</button></form><ul id=l></ul>", encoding="utf-8")
    assert ui_chaos.ergonomics(page) == []


def test_standing_preferences_reach_ordinary_chat(data):
    import assistant_prep
    import preferences

    preferences.remember("Bundan sonra her zaman yanıtlarının sonuna 'Kolay gelsin' yaz.")
    messages, *_rest = assistant_prep.build_llm_stream_inputs(
        {"prompt": "Stok nasıl sayılır?", "full_prompt": "Stok nasıl sayılır?", "image_b64": None, "history": "[]", "user_id": "default",
         "conversation_id": "t", "has_file": False, "is_prompt_conv": False, "custom_agent": None}, "Sistem", "")
    assert messages[0]["role"] == "system" and "Kolay gelsin" in messages[0]["content"]


def test_a_patch_that_is_really_a_rewrite_is_refused_and_lint_is_fixed_without_a_model(tmp_path):
    import patch_edit
    import tier0_edit

    current = "\n".join(f"<p>{i}</p>" for i in range(300))

    async def generate(_system, _user):
        return "<<<<<<< SEARCH\n" + "\n".join(current.split("\n")[:250]) + "\n=======\n<p>yeni</p>\n>>>>>>> REPLACE"

    assert asyncio.run(patch_edit.try_patch(generate, "değiştir", current)) is None
    (tmp_path / "a.py").write_text("import os\nimport sys\n\nprint(sys.argv)\n", encoding="utf-8")
    assert tier0_edit.apply(tmp_path, "lint hatalarını düzelt") == ["a.py"]
    assert "import os" not in (tmp_path / "a.py").read_text(encoding="utf-8")
    assert tier0_edit.apply(tmp_path, "lint nedir") == []


def test_feedback_winner_merge_regression_guard_and_time_chart(data, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import app as app_module
    import config
    import feedback
    import perf_report
    import variants
    import workspace_builder as wb
    import workspace_smoke

    monkeypatch.setattr(config, "WORKSPACES_DIR", tmp_path / "ws")
    for name, body in (("ana-1", "ana"), ("var-a", "A hali"), ("var-b", "B hali")):
        folder = wb.safe_workspace_dir(name)
        folder.mkdir(parents=True)
        (folder / "index.html").write_text(body, encoding="utf-8")
    client = TestClient(app_module.app)
    assert client.post("/api/studio/workspaces/ana-1/feedback", json={"verdict": "down", "note": "buton küçük"}).status_code == 200
    client.put("/api/studio/workspaces/ana-1/file", json={"path": "index.html", "content": "elle"})
    assert [e["kind"] for e in feedback.load()] == ["beğenilmedi", "elle düzenleme"]
    variants.remember("ana-1", {"A": "var-a", "B": "var-b"})
    assert "ana projeye" in variants.merge_winner("B") and (wb.safe_workspace_dir("ana-1") / "index.html").read_text(encoding="utf-8") == "B hali"
    assert variants._WINNER_RE.match("A varyantını ana projeye al") and not variants._WINNER_RE.match("iki varyant yap")
    app_file = wb.safe_workspace_dir("ana-1") / "main.py"
    app_file.write_text("x = 1\n", encoding="utf-8")
    workspace_smoke._guard_regression(wb.safe_workspace_dir("ana-1"), app_file)
    assert 'import_module("main")' in (wb.safe_workspace_dir("ana-1") / "tests" / "test_regression_startup.py").read_text(encoding="utf-8")
    chart = perf_report.stage_chart([{"stage": "plan", "seconds": 4}], [{"name": "<workspace>", "total_s": 30}])
    assert chart.startswith("![Zaman") and perf_report.stage_chart([], []) == ""


def test_a_secret_in_a_request_never_reaches_the_run_record(data):
    import run_control

    key = "sk-proj-" + "Zz91" * 10
    run = run_control.start(f"sayfa yap (anahtarım {key})\n\nKULLANICININ KALICI TERCİHLERİ: x")
    run.add_node("a", title="a", purpose=f"anahtar {key}")
    run.steer(f"şunu kullan {key}")
    run.update("a", error=f"hata {key}")
    saved = (data / "runs" / f"{run.id}.jsonl").read_text(encoding="utf-8")
    assert key not in saved and "TERCİHLERİ" not in saved and key in run.notes[-1]


def test_symbols_with_lines_for_every_language_and_script_merge():
    pytest.importorskip("tree_sitter_javascript")
    import semantic_merge
    import ts_symbols

    assert "def topla  L1-3" in ts_symbols.outline("function topla(a) {\n  return a;\n}\n", ".js")
    assert "var --ana  L1-1" in ts_symbols.outline(":root { --ana: #123456; }", ".css")
    assert "#liste  L1-1" in ts_symbols.outline("<ul id='liste'></ul>", ".html")
    assert any(x.startswith("table ") for x in ts_symbols.outline("CREATE TABLE notlar (id INTEGER);", ".sql"))
    assert "route GET /api/x  L1" in ts_symbols.outline("app.get('/api/x', h)\n", ".js")
    base = "const a = 1;\n\nfunction topla(x) {\n  return x;\n}\n\nfunction etiket(y) {\n  return y;\n}\n"
    ours = base.replace("return x;", "return x + a;")
    theirs = base.replace("return y;", "return String(y);")
    merged, conflicts = semantic_merge.merge_script(base, ours, theirs, ".js")
    assert not conflicts and "return x + a;" in merged and "return String(y);" in merged
    renamed = base.replace("function topla(", "function toplam(")
    merged, conflicts = semantic_merge.merge_script(base, renamed, ours, ".js")
    assert not conflicts and "function toplam(x)" in merged and "return x + a;" in merged and "function topla(x)" not in merged
    clash = semantic_merge.merge_script(base, ours, base.replace("return x;", "return x * 2;"), ".js")[1]
    assert [c.name for c in clash] == ["def topla"]
    assert semantic_merge.merge_script(base, "function (", base, ".js") is None


def test_web_linters_report_real_mistakes(tmp_path):
    import static_lint

    if not static_lint.available():
        pytest.skip("lint araçları kurulu değil")
    (tmp_path / "a.js").write_text("function f() { return olmayanDegisken; }\nf();\n", encoding="utf-8")
    (tmp_path / "a.css").write_text("a { colr: red; color: #zzzzzz; }\n", encoding="utf-8")
    (tmp_path / "a.html").write_text("<div id=x></div><div id=x></Div>\n", encoding="utf-8")
    found = " | ".join(static_lint.findings(tmp_path))
    assert "olmayanDegisken" in found and "colr" in found and "a.html" in found, found


def test_a_key_in_a_build_request_is_removed_before_anything_is_written(tmp_path, monkeypatch):
    import config
    import workspace_builder as wb

    monkeypatch.setattr(config, "WORKSPACES_DIR", tmp_path)
    key = "sk-proj-" + "Zz91" * 10
    seen = []

    async def model(*_a, **kwargs):
        seen.append(str(kwargs.get("user", "")))
        return '{"name": "x", "files": [{"path": "index.html", "purpose": "sayfa"}]}'

    async def pick(_m=None):
        return "m"

    async def files(ws_dir, meta, request, model_name, planned):
        seen.append(request)
        if False:
            yield {}

    monkeypatch.setattr(wb, "_ollama_generate", model)
    monkeypatch.setattr(wb, "pick_coder_model", pick)
    monkeypatch.setattr(wb.build_dag, "generate_files", files)

    async def go():
        return [e async for e in wb.stream_generate_project(f"sayfa yap (anahtarım {key})", run_smoke=False)]

    asyncio.run(go())
    stored = "".join(p.read_text(encoding="utf-8", errors="ignore") for p in tmp_path.rglob("*") if p.is_file())
    assert stored and key not in stored and not any(key in s for s in seen) and len(seen) >= 2


def test_mcp_connector_refuses_metadata_addresses_but_allows_local_servers():
    import mcp_connector

    for bad in ("http://169.254.169.254/latest", "http://[::ffff:169.254.169.254]/", "http://[fe80::1]/", "http://0.0.0.0/", "http://metadata.google.internal/x"):
        with pytest.raises(ValueError, match="bağlanılamaz"):
            mcp_connector._refuse_metadata(bad)
    mcp_connector._refuse_metadata("http://127.0.0.1:8123/mcp")
    mcp_connector._refuse_metadata("http://192.168.1.10/mcp")


def test_server_commands_need_a_project_and_say_why(tmp_path):
    import project_server

    assert project_server.answer("sunucuyu başlat nasıl yapılır anlat", tmp_path) == ""
    assert "proje yok" in project_server.answer("sunucuyu başlat", None)
    assert project_server.answer("sunucu durumu", None) == "Çalışan proje sunucusu yok."
    assert "açılamadı" in project_server.answer("sunucuyu başlat", tmp_path)


def test_no_slide_text_is_smaller_than_14_points():
    from pptx import Presentation
    from pptx.dml.color import RGBColor

    import deck_layouts

    deck = Presentation()
    paragraph = deck.slides.add_slide(deck.slide_layouts[6]).shapes.add_textbox(0, 0, 914400, 914400).text_frame.paragraphs[0]
    deck_layouts._add_run(paragraph, "dipnot", 9.0, RGBColor(0, 0, 0))
    assert paragraph.runs[0].font.size.pt == 14
    assert deck_layouts._bullet_metrics(["x" * 400] * 8, wide=False)[0] == 14
    assert deck_layouts._step_size(["x" * 200] * 6) == 14


def test_pdf_flow_reports_orphan_heading_and_blank_last_page(tmp_path):
    import pymupdf

    import office_verify

    def make(name, orphan, blank):
        doc = pymupdf.open()
        page = doc.new_page()
        for i in range(30):
            page.insert_text((40, 60 + i * 20), "Govde metni satiri burada devam ediyor.", fontsize=10)
        if orphan:
            page.insert_text((40, 740), "Yeni Bolum", fontsize=15, fontname="hebo")
        second = doc.new_page()
        if not blank:
            second.insert_text((40, 80), "Bolumun metni.", fontsize=10)
        second.insert_text((40, 820), "Sayfa 2 / 2", fontsize=8)
        doc.save(tmp_path / name)
        doc.close()
        return " | ".join(office_verify.check_pdf(tmp_path / name))

    assert "tek kalmış: Yeni Bolum" in make("a.pdf", True, False)
    assert "sayfa boş" in make("b.pdf", False, True)
    clean = make("c.pdf", False, False)
    assert "tek kalmış" not in clean and "sayfa boş" not in clean, clean


def test_research_connectors_carry_dates_and_offline_docs_answer_without_network(tmp_path, monkeypatch):
    import json

    import config
    import research_sources

    atom = (b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/1</id><title>Speculative Decoding</title>'
            b'<published>2024-03-02T00:00:00Z</published><summary>Draft tokens.</summary><author><name>A B</name></author></entry></feed>')
    repo = {"items": [{"html_url": "https://github.com/a/b", "full_name": "a/b", "description": "d", "stargazers_count": 3, "language": "Python",
                       "license": None, "open_issues_count": 0, "pushed_at": "2026-10-01T00:00:00Z"}]}
    asked = []

    def fake(url):
        asked.append(url)
        return atom if "arxiv" in url else json.dumps(repo).encode()

    monkeypatch.setattr(research_sources, "_get", fake)
    pages = research_sources.online("speculative decoding hakkında arxiv makalesi ve github deposu")
    assert [p.dated_title() for p in pages] == ["arXiv: Speculative Decoding (yayın/güncelleme: 2024-03-02)", "GitHub: a/b (yayın/güncelleme: 2026-10-01)"]
    assert research_sources.online("yemek tarifi anlat") == [] and len(asked) == 2

    folder = tmp_path / "vendor" / "docs" / "sqlite"
    folder.mkdir(parents=True)
    (folder / "index.json").write_text(json.dumps({"entries": [{"name": "busy_timeout pragma", "path": "pragma#busy_timeout"}]}), encoding="utf-8")
    (folder / "db.json").write_text(json.dumps({"pragma": "<h1>PRAGMA busy_timeout</h1><p>" + "Sets the busy handler timeout. " * 12 + "</p>"}), encoding="utf-8")
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    research_sources._docset.cache_clear()
    found = research_sources.offline_docs("sqlite busy_timeout nasıl ayarlanır")
    research_sources._docset.cache_clear()
    assert found and found[0].url == "https://devdocs.io/sqlite/pragma" and "busy handler" in found[0].text and "<p>" not in found[0].text


def test_workbook_finance_formulas_recalculate_and_loops_or_narrow_columns_are_reported(tmp_path):
    from openpyxl import Workbook, load_workbook

    import office_verify
    import xlsx_builder
    import xlsx_checks

    spec = xlsx_builder.parse_spec({"title": "Yatırım", "sheets": [{"name": "Akis", "headers": ["Yıl", "Nakit Akışı"], "rows": [["2027", -1000], ["2028", 600], ["2029", 700]],
                                    "summary": [{"label": "NBD", "function": "NPV", "column": "Nakit Akışı", "rate": 0.1}, {"label": "IVO", "function": "IRR", "column": "Nakit Akışı"},
                                                {"label": "2028 akışı", "function": "XLOOKUP", "lookup": "2028", "in": "Yıl", "return": "Nakit Akışı"}]}]})
    path = tmp_path / "f.xlsx"
    spec["sheets"][0]["summary"].append({"label": "Toplam planlanan nakit girişi", "function": "SUM", "column": "Nakit Akışı"})
    xlsx_builder.build_workbook(path, spec)
    assert xlsx_checks.problems(path) == []
    formulas = [c.value for row in load_workbook(path)["Akis"].iter_rows() for c in row if str(c.value).startswith("=")]
    assert any(f.startswith("=NPV(0.1,B5:B7)") for f in formulas) and "=IRR(B5:B7)" in formulas and any("XLOOKUP" in f for f in formulas), formulas
    if office_verify.soffice():
        converted = office_verify._convert(path, "xlsx", tmp_path / "out")
        values = [c.value for row in load_workbook(converted, data_only=True)["Akis"].iter_rows() for c in row]
        assert any(isinstance(v, float) and 0.18 < v < 0.19 for v in values), values  # IRR of -1000, 600, 700
        assert office_verify.check(path) == []

    bad = Workbook()
    sheet = bad.active
    sheet["A1"], sheet["B1"], sheet["C1"] = "=B1+1", "=C1*2", "=A1"
    sheet["A2"], sheet["B2"] = "çok uzun bir açıklama metni burada", 1
    sheet["C3"] = 123456789012
    found = " | ".join(xlsx_checks.circular_references(bad) + xlsx_checks.clipped_cells(bad))
    assert "döngüsel başvuru" in found and "A2: sütun dar, metin kesilir" in found and "C3: sütun dar, sayı" in found, found


def test_sensitivity_and_numeric_requests_are_computed_not_guessed():
    pytest.importorskip("scipy")
    import science_kernel

    table = science_kernel.answer("duyarlılık: kâr = (fiyat - maliyet) * adet; fiyat=100; maliyet=60; adet=1000; ±%10")
    assert "temel durum): 40,000.00" in table and "En çok etkileyen: **fiyat**" in table and "| fiyat | 30,000.00 | 50,000.00 | 20,000.00 | 2.50 |" in table
    assert "0.746824" in science_kernel.answer("sayısal integral: exp(-x^2); x=0..1")
    assert "0.73908513" in science_kernel.answer("sayısal kök: cos(x) - x; x=0..1")
    assert "x ≈ 2" in science_kernel.answer("en küçük değer: x^2 - 4x + 7; x=0..10")
    for attack in ("sayısal kök: __import__('os'); x=0..1", "sayısal kök: x.__class__; x=0..1", "duyarlılık: a = open(b); b=1", "sayısal integral: x^99999; x=0..1"):
        assert science_kernel.answer(attack).startswith("Hesaplanamadı"), attack
    assert science_kernel.answer("duyarlılık nedir anlat") == ""


def test_feature_flags_fill_only_what_is_unset_and_profiles_override(tmp_path):
    import json

    import feature_flags

    path = tmp_path / "c.json"
    path.write_text(json.dumps({"features": {"enable_web": False, "enable_self_play": True, "bilinmeyen": True}, "profiles": {"sessiz": {"enable_self_play": False}}}), encoding="utf-8")
    env = {"WEB_GROUNDING": "1"}
    assert feature_flags.apply(path=path, environ=env) == ["enable_self_play=açık"] and env == {"WEB_GROUNDING": "1", "SELF_PLAY_HOUR": "4"}
    env = {}
    feature_flags.apply("sessiz", path=path, environ=env)
    assert env == {"WEB_GROUNDING": "0", "SELF_PLAY_HOUR": ""}
    with pytest.raises(ValueError, match="profil yok"):
        feature_flags.chosen("olmayan", path)


def test_dependency_audit_sends_only_names_and_versions(tmp_path):
    import dependency_audit

    (tmp_path / "requirements.txt").write_text("flask==0.5\nhttpx>=0.2\nrequests[socks]==2.0.0\n", encoding="utf-8")
    sent = []

    def post(path, body):
        sent.append(body)
        return {"results": [{"vulns": [{"id": "GHSA-x"}]}, {}]}

    text = dependency_audit.answer("bağımlılık denetimi", tmp_path, tmp_path, post)
    assert "2 bağımlılığın 1 tanesinde" in text and "flask 0.5" in text and "GHSA-x" in text
    assert sent == [{"queries": [{"package": {"ecosystem": "PyPI", "name": "flask"}, "version": "0.5"}, {"package": {"ecosystem": "PyPI", "name": "requests"}, "version": "2.0.0"}]}]
    assert dependency_audit.answer("bağımlılık nedir", tmp_path, tmp_path, post) == ""


def test_a_file_saved_by_another_program_is_noticed_and_the_daily_summary_lists_it(tmp_path, monkeypatch):
    import os
    import time

    import config
    import event_log
    import external_watch
    import night_summary

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(config, "WORKSPACES_DIR", tmp_path / "ws")
    (tmp_path / "data").mkdir()
    project = tmp_path / "ws" / "p1"
    project.mkdir(parents=True)
    (project / "main.py").write_text("x = 1\n", encoding="utf-8")
    assert external_watch.scan() == [] and external_watch.scan() == []  # first look only remembers
    (project / "main.py").write_text("def f(:\n", encoding="utf-8")
    os.utime(project / "main.py", (time.time() + 60, time.time() + 60))
    assert external_watch.scan() == ["p1"] and external_watch.scan() == []
    kinds = [e["kind"] for e in event_log.read(project)]
    assert "dışarıdan değişiklik" in kinds and "dış değişiklikten sonra sorun" in kinds and (project / ".history").is_dir(), kinds
    event_log.record(project, "sürüm kaydedildi", "platform")
    (project / "main.py").write_text("x = 2\n", encoding="utf-8")
    assert external_watch.scan() == []  # the platform recorded this change itself
    text = night_summary.answer("gece özeti")
    assert "p1:" in text and "dış değişiklikten sonra sorun" in text and "## Sistem" in text


def test_memory_facts_can_be_pinned_expired_and_forgotten_for_good(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta

    import memory_engine
    import memory_maintenance
    import memory_marks
    import memory_timeline

    monkeypatch.setattr(memory_engine, "_memory_db_path", lambda: tmp_path / "m.db")
    memory_timeline.install()
    for key, value in (("a", "koyu tema"), ("b", "FastAPI"), ("c", "emoji yok")):
        memory_engine.upsert_semantic_fact("preference", key, value, "u")
    ids = {f["fact_key"]: f["id"] for f in memory_engine.list_semantic_facts("u")}
    assert "sabitlendi" in memory_marks.answer(f"hafıza {ids['a']} sabitle", "u")
    assert "tarihinde unutulacak" in memory_marks.answer(f"hafıza #{ids['b']} süre 30 gün", "u")
    assert memory_engine.build_memory_context_block("FastAPI", "u").splitlines()[1] == "- [preference] koyu tema"  # pinned beats relevance
    assert "(sabit)" in memory_marks.answer("hafızamı göster", "u")
    far = datetime.now(UTC) + timedelta(days=4000)
    with memory_engine._connect() as conn:  # inside an open write, pins are still readable
        conn.execute("UPDATE semantic_memories SET confidence = confidence WHERE user_id = 'u'")
        assert len(memory_marks.pinned_ids(conn)) == 1
    with memory_engine._connect() as conn:
        assert memory_maintenance.prune_faded(conn, "u", far) == 2  # the pinned one never fades
    memory_engine.upsert_semantic_fact("preference", "b", "FastAPI", "u")
    fresh = {f["fact_key"]: f for f in memory_engine.list_semantic_facts("u")}["b"]
    assert not fresh["pinned"] and not fresh["expires_at"]  # nothing inherited from the pruned fact
    memory_marks.answer(f"hafıza {fresh['id']} süre 30 gün", "u")
    later = memory_marks.apply(memory_engine.list_semantic_facts("u"), "u", datetime.now(UTC) + timedelta(days=31))
    assert [f["fact_key"] for f in later] == ["a"]
    assert "kalıcı olarak silindi" in memory_marks.answer(f"hafıza {ids['a']} kalıcı sil", "u")
    assert memory_engine.list_semantic_facts("u") == [] and memory_timeline.history("a", "u") == []
    assert "yok" in memory_marks.answer("hafıza 999 sabitle", "u") and memory_marks.answer("hafıza nedir", "u") == ""


def test_random_actions_catch_an_api_whose_list_disagrees_with_what_was_done():
    import httpx

    import state_property

    def server(forget_deletes):
        rows, counter = {}, [0]

        def handle(request):
            path = request.url.path
            if request.method == "POST":
                counter[0] += 1
                rows[counter[0]] = {"id": counter[0], **__import__("json").loads(request.content)}
                return httpx.Response(201, json=rows[counter[0]])
            if request.method == "DELETE":
                if not forget_deletes:
                    rows.pop(int(path.rsplit("/", 1)[1]))
                return httpx.Response(204)
            return httpx.Response(200, json={"items": list(rows.values())})

        return httpx.Client(transport=httpx.MockTransport(handle), base_url="http://x")

    spec = {"paths": {"/api/n": {"get": {}, "post": {"requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/N"}}}}}},
                      "/api/n/{i}": {"delete": {}}}, "components": {"schemas": {"N": {"properties": {"metin": {"type": "string"}, "adet": {"type": "integer"}}}}}}
    resource = state_property.resources(spec)[0]
    assert resource.item == "/api/n/{i}" and resource.fields == {"metin": "string", "adet": "integer"}
    good, alive = state_property.exercise(server(False), resource)
    assert good.problems == [] and alive and all(alive.values()), good.problems
    bad, _alive = state_property.exercise(server(True), resource)
    assert bad.problems and "uyuşmuyor" in bad.problems[0]


def test_decisions_become_numbered_records_and_root_causes_fill_the_notebook(tmp_path, monkeypatch):
    import config
    import decisions

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    project = tmp_path / "p"
    project.mkdir()
    assert "001-veritabani-olarak-sqlite" in decisions.answer("karar: veritabanı olarak SQLite kullanacağız çünkü tek bilgisayarda çalışacak", project)
    text = next((project / "docs" / "adr").glob("001-*.md")).read_text(encoding="utf-8")
    assert "## Gerekçe\n\ntek bilgisayarda çalışacak" in text
    assert decisions.note("Arayüzü sade tutmaya karar verdik. Şimdi listeyi ekle.", project).startswith("002-")
    assert decisions.note("Arayüzü sade tutmaya karar verdik.", project).startswith("002-")  # not twice
    assert decisions.note("Karar verdik mi?", project) == "" and decisions.answer("liste ekle", project) == ""
    listing = decisions.answer("mimari kararları göster", project)
    assert "ADR 001" in listing and "ADR 002" in listing
    decisions.learned("p1", "indeks bir fazla başlatılmış")
    decisions.learned("p2", "indeks bir fazla başlatılmış")
    assert decisions.lessons().count("indeks") == 1 and "[p1]" in decisions.answer("defteri göster", None)


def test_code_is_moved_and_signatures_migrated_without_breaking_callers(tmp_path):
    import subprocess

    import refactor_move
    import workspace_commands

    (tmp_path / "araclar.py").write_text("import math\n\nSINIR = 10\n\n\ndef alan(yaricap, oran=1):\n    return round(math.pi * yaricap ** 2 * oran, 2)\n\n\n"
                                         "def kare(x):\n    return x * x\n\n\ndef sinirli(x):\n    return min(x, SINIR)\n", encoding="utf-8")
    (tmp_path / "ana.py").write_text("from araclar import alan, kare\n\nprint(alan(1, oran=2), alan(2), kare(3))  # alan: açıklama\n", encoding="utf-8")

    def output():
        return subprocess.run([sys.executable, "ana.py"], cwd=tmp_path, capture_output=True, text=True, check=True).stdout

    before = output()
    assert workspace_commands.parse("alan ve kare fonksiyonlarını geometri modülüne taşı")[0] == "restructure"
    assert refactor_move.run(tmp_path, *refactor_move.parse("alan ve kare fonksiyonlarını geometri modülüne taşı")) == ["geometri.py", "araclar.py"]
    moved = (tmp_path / "geometri.py").read_text(encoding="utf-8")
    assert moved.startswith("import math") and "def alan" in moved and "def alan" not in (tmp_path / "araclar.py").read_text(encoding="utf-8")
    assert output() == before
    assert refactor_move.run(tmp_path, *refactor_move.parse("alan fonksiyonunda oran parametresini carpan yap")) == ["ana.py", "geometri.py"]
    assert "alan(1, carpan=2)" in (tmp_path / "ana.py").read_text(encoding="utf-8") and "# alan: açıklama" in (tmp_path / "ana.py").read_text(encoding="utf-8")
    assert refactor_move.run(tmp_path, *refactor_move.parse("kare fonksiyonuna us parametresi ekle varsayılan 2")) == ["geometri.py"]
    assert "def kare(x, us=2):" in (tmp_path / "geometri.py").read_text(encoding="utf-8") and output() == before
    for bad, why in (("sinirli fonksiyonunu yeni modülüne taşı", "döngüsel"), ("kare fonksiyonuna k parametresi ekle varsayılan open('x')", "malformed")):
        with pytest.raises(ValueError, match=why):
            refactor_move.run(tmp_path, *refactor_move.parse(bad))
    assert not (tmp_path / "yeni.py").exists() and output() == before


def test_every_finish_check_runs_for_a_page_and_for_a_script(tmp_path, monkeypatch):
    import asyncio

    import post_checks

    ran = []

    def stub(name):
        return lambda *a, **k: ran.append(name) or ""

    for module in ("security_scan", "flow_analysis", "visual_audit", "design_slop", "package_check", "code_audit", "migration_check", "ui_chaos", "api_fuzz", "leak_check"):
        monkeypatch.setattr(getattr(post_checks, module), "report", stub(module))
    monkeypatch.setattr(post_checks.deploy_kit, "apply", lambda *a: "")
    monkeypatch.setattr(post_checks.provenance, "write", lambda *a: None)
    written = []
    monkeypatch.setattr(post_checks.ledger, "write", lambda _ws, entry: written.append(entry))
    done = asyncio.run(post_checks.apply(tmp_path, "küçük bir betik", {"warnings": []}))
    assert done["warnings"] == [] and len(ran) == 10, ran
    assert not any("yerleşim" in line or "sızıntı" in line for line in written[-1]["verified"]), written  # no page, no claim
    ran.clear()
    (tmp_path / "index.html").write_text("<p>a</p>", encoding="utf-8")
    asyncio.run(post_checks.apply(tmp_path, "sayfa", {}))
    assert len(ran) == 10 and any("yerleşim" in line for line in written[-1]["verified"]), written


def test_a_page_that_keeps_growing_is_reported_and_a_steady_one_is_not(tmp_path):
    import leak_check

    steady = "<button type='button' onclick=\"document.getElementById('n').textContent++\">say</button><p id='n'>0</p>"
    leaking = ("<button type='button' id='b'>ekle</button><div id='l'></div><script>const keep = [];\n"
               "document.getElementById('b').addEventListener('click', () => { for (let i = 0; i < 5; i++) { const d = document.createElement('div'); d.addEventListener('click', () => d); "
               "document.getElementById('l').append(d); keep.push(d); } });</script>")
    results = {}
    for name, markup in (("sabit", steady), ("sizan", leaking)):
        (tmp_path / f"{name}.html").write_text(markup, encoding="utf-8")
        try:
            results[name] = leak_check.measure((tmp_path / f"{name}.html").as_uri(), cycles=30)
        except ValueError:
            pytest.skip("tarayıcı yok")
    assert results["sabit"].leaks() == [], results["sabit"]
    found = " | ".join(results["sizan"].leaks())
    assert "DOM öğesi" in found and "olay dinleyicisi" in found, found
    assert "| DOM öğesi |" in leak_check.compare(results["sizan"], results["sabit"])


def test_a_timed_out_command_takes_its_grandchildren_with_it(tmp_path):
    import time

    import psutil

    import process_utils

    if sys.platform != "win32":
        pytest.skip("Windows iş nesnesi")
    marker = tmp_path / "torun.pid"
    child = (f"import subprocess, sys, time\np = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
             f"open({str(marker)!r}, 'w').write(str(p.pid))\ntime.sleep(60)\n")
    began = time.time()
    done = process_utils.run_process([sys.executable, "-c", child], timeout_s=4)
    assert done.timed_out and time.time() - began < 20
    pid = int(marker.read_text())
    for _wait in range(50):
        if not psutil.pid_exists(pid):
            break
        time.sleep(0.1)
    assert not psutil.pid_exists(pid), "torun süreç hayatta kaldı"
    assert process_utils.run_process([sys.executable, "-c", "print('İğne')"]).stdout.strip() == "İğne"


def test_concurrent_writers_queue_instead_of_failing(tmp_path):
    import threading

    import dbconn

    path = tmp_path / "y.db"
    with dbconn.connection(path) as conn:
        conn.execute("CREATE TABLE s (n INTEGER)")
    errors = []

    def work(worker):
        try:
            for i in range(25):
                with dbconn.open_db(path) as conn:
                    conn.execute("INSERT INTO s VALUES (?)", (worker * 100 + i,))
                    conn.execute("UPDATE s SET n = n WHERE n = -1")
        except Exception as exc:  # collected and asserted below
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(w,)) for w in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(60)
    with dbconn.connection(path) as conn:
        assert errors == [] and conn.execute("SELECT COUNT(*) FROM s").fetchone()[0] == 400
    assert dbconn.writer_lock(path).acquire(blocking=False), "yazma kilidi geri verilmemiş"
    dbconn.writer_lock(path).release()
    first = dbconn.open_db(path)
    first.execute("INSERT INTO s VALUES (1)")
    assert first.held
    first.rollback()
    assert not first.held
    first.close()


def test_schema_change_is_preceded_by_a_backup_and_only_own_images_are_pruned(tmp_path, monkeypatch):
    import config
    import db
    import db_health
    import disk_gc

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "platform.db"))
    db.init_db()
    with db.connect() as conn:
        conn.execute("UPDATE schema_version SET version = 1")
    copies = []
    monkeypatch.setattr(db_health, "hot_backup", lambda path, label="manual": copies.append(label))
    db.init_db()
    assert copies == ["gecis"]
    db.init_db()
    assert copies == ["gecis"]
    seen = []

    class Done:
        returncode, stdout = 0, "Total reclaimed space: 12MB\n"

    monkeypatch.setattr(disk_gc.shutil, "which", lambda name: "docker")
    assert disk_gc.prune_images(run=lambda args, **k: seen.append(args) or Done()) == "Total reclaimed space: 12MB"
    assert seen == [["docker", "image", "prune", "--force", "--filter", "label=cm6453"]]


VENDOR = __import__("pathlib").Path(__file__).resolve().parents[1] / "data" / "vendor"  # downloaded vault; tests skip without it


def test_flow_extras_cross_less_clip_nothing_and_open_without_network(tmp_path, monkeypatch):
    import flowchart_studio
    import interactive_artifacts

    monkeypatch.setattr(interactive_artifacts, "vault", lambda: VENDOR)

    flow = {"title": "Sipariş <akışı>", "steps": [{"id": i, "type": t, "label": lbl} for i, t, lbl in
            (("a", "start", "Sipariş al"), ("b", "process", "Stok ayır"), ("c", "process", "Ödeme al"), ("d", "end", "Kargola"), ("e", "end", "Fatura </script> kes"))],
            "edges": [{"from": "a", "to": "b", "label": ""}, {"from": "a", "to": "c", "label": ""}, {"from": "b", "to": "e", "label": ""}, {"from": "c", "to": "d", "label": ""}]}
    depth = {"a": 0, "b": 1, "c": 1, "d": 2, "e": 2}
    layers = {0: ["a"], 1: ["b", "c"], 2: ["d", "e"]}
    assert flowchart_studio.crossings(flow, layers, depth) == 1
    flowchart_studio._uncross(flow, layers, depth)
    assert flowchart_studio.crossings(flow, layers, depth) == 0 and layers[2] == ["e", "d"]
    assert flowchart_studio.clipped_labels(flow) == []
    long = {"steps": [{"label": "Bu etiket kutunun üç satırına kesinlikle sığmayacak kadar uzun yazılmış bir açıklamadır gerçekten"}]}
    assert flowchart_studio.clipped_labels(long)
    d2 = interactive_artifacts.d2_text(flow)
    assert 'n1: "Sipariş al" { shape: oval }' in d2 and "n1 -> n2" in d2
    if interactive_artifacts.d2_program():
        target = tmp_path / "a.svg"
        assert interactive_artifacts.d2_svg(d2, target) and "Sipariş al" in target.read_text(encoding="utf-8")


@pytest.mark.parametrize(("library", "selector"), [("vega", "#view svg path"), ("plotly", "#view .bars path"), ("chart.js", "#view canvas"), ("cytoscape", "#view canvas")])
def test_interactive_file_really_draws_with_the_network_cut(tmp_path, monkeypatch, library, selector):
    import interactive_artifacts

    monkeypatch.setattr(interactive_artifacts, "vault", lambda: VENDOR)
    if not interactive_artifacts.available(library):
        pytest.skip("kütüphane kasada yok")
    sync = pytest.importorskip("playwright.sync_api")
    data = ({"elements": [{"data": {"id": "a", "label": "A", "kind": "start"}}, {"data": {"id": "b", "label": "B", "kind": "end"}}, {"data": {"source": "a", "target": "b", "label": ""}}]}
            if library == "cytoscape" else interactive_artifacts.chart_data("Şube", "Satış", [("İzmir </script>", 5.0), ("Muş", 3.0)]))
    target = tmp_path / "g.html"
    target.write_text(interactive_artifacts.page(library, "Deneme", data), encoding="utf-8")
    with sync.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except sync.Error:
            pytest.skip("tarayıcı yok")
        context = browser.new_context(offline=True)
        page = context.new_page()
        errors, outside = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda r: outside.append(r.url) if r.url.startswith("http") else None)
        page.goto(target.as_uri())
        page.wait_for_selector(selector, state="attached", timeout=15000)
        browser.close()
    assert errors == [] and outside == [], (errors, outside)


def test_definition_hover_and_conditional_breakpoint_come_from_the_real_servers(tmp_path):
    import debug_probe
    import workspace_commands
    import workspace_docker

    (tmp_path / "hesap.py").write_text('def indirim(tutar: float) -> float:\n    """Yüz liradan fazlasına indirim."""\n    sonuc = tutar\n    if tutar > 100:\n        sonuc = tutar - 10\n    return sonuc\n', encoding="utf-8")
    (tmp_path / "ana.py").write_text("from hesap import indirim\n\nprint(indirim(5))\n", encoding="utf-8")
    assert workspace_commands.parse("indirim nerede tanımlı?") == ("inspect", "indirim nerede tanımlı?")
    assert debug_probe.asked("koşullu kesme: ../x.py:1") is None
    answer = workspace_commands._inspect(tmp_path, "indirim tanımına git")
    assert "hesap.py:1" in answer, answer
    info = workspace_commands._inspect(tmp_path, "indirim imzası")
    assert "tutar: float" in info and "indirim" in info, info
    if not workspace_docker.available():
        pytest.skip("Docker kapalı")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_hesap.py").write_text("from hesap import indirim\n\n\ndef test_hepsi():\n    for tutar in (50, 150, 500):\n        indirim(tutar)\n", encoding="utf-8")
    hit = workspace_commands._inspect(tmp_path, "koşullu kesme: hesap.py:6 tutar > 400")
    assert "kesme noktasında durdu" in hit and "tutar=500" in hit and "sonuc=490" in hit, hit
    assert "durulmadı" in workspace_commands._inspect(tmp_path, "koşullu kesme: hesap.py:6 tutar > 9000")


def test_document_commands_read_contents_pages_tables_and_check_quotes(tmp_path):
    import pymupdf

    import doc_tools

    doc = pymupdf.open()
    for number, body in enumerate(("Depo raporu. Stok devir hizi 2026 yilinda 7,4 oldu.", "Ikinci sayfa: iade orani yuzde 3."), 1):
        page = doc.new_page()
        page.insert_text((50, 60), body, fontsize=11)
        if number == 2:
            for row, cells in enumerate((("Urun", "Adet"), ("Kalem", "12"), ("Defter", "30"))):
                for col, cell in enumerate(cells):
                    rect = pymupdf.Rect(50 + col * 100, 100 + row * 20, 150 + col * 100, 120 + row * 20)
                    page.draw_rect(rect)
                    page.insert_text((rect.x0 + 4, rect.y1 - 5), cell, fontsize=10)
    doc.set_toc([[1, "Giris", 1], [2, "Iadeler", 2]])
    raw = doc.tobytes()
    doc.close()
    assert "- Giris (sayfa 1)\n  - Iadeler (sayfa 2)" in doc_tools.answer("içindekiler", "r.pdf", raw)
    second = doc_tools.answer("sayfa 2", "r.pdf", raw)
    assert "iade orani" in second and "Depo raporu" not in second
    assert "geçersiz" in doc_tools.answer("sayfa 5-9", "r.pdf", raw)
    table = doc_tools.answer("tabloları çıkar", "r.pdf", raw)
    assert "| Urun | Adet |" in table and "| Defter | 30 |" in table, table
    assert "birebir var**: sayfa 1" in doc_tools.answer('alıntıyı doğrula: "Stok devir hizi 2026 yilinda 7,4 oldu."', "r.pdf", raw)
    wrong = doc_tools.answer('alıntıyı doğrula: "Stok devir hizi 2026 yilinda 9,9 oldu."', "r.pdf", raw)
    assert "birebir yok" in wrong and "7,4" in wrong
    assert doc_tools.answer("belgeyi anlat", "r.pdf", raw) == ""
    assert "- Başlık (satır 1)" in doc_tools.answer("içindekiler", "n.md", "# Başlık\nmetin\n".encode())


def test_summary_tree_is_written_to_disk_and_reused(tmp_path, monkeypatch):
    import asyncio
    import json

    import config
    import doc_tree

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    calls = []

    async def chat(system, user, schema):
        calls.append(1)
        return json.dumps({"summary": "Depo düzeni anlatılıyor.", "quotes": []})

    text = ("Depo düzeni anlatılıyor. " * 40 + "\n") * 12

    async def run(model):
        reports = [value async for kind, value in doc_tree.summarise(text, model) if kind == "report"]
        return reports[-1]

    first = asyncio.run(run(chat))
    stored = list((tmp_path / "doc_trees").glob("*.json"))
    assert len(stored) == 1 and calls and json.loads(stored[0].read_text(encoding="utf-8"))["leaves"]
    monkeypatch.setattr(doc_tree.research, "_ask", lambda *a: pytest.fail("model yeniden çağrıldı"))
    assert asyncio.run(run(None)) == first


def test_a_two_or_three_slide_request_can_be_satisfied():
    import deep_research

    def spec(count):
        return {"slides": [{"title": f"Başlık {i}", "bullets": ["Raf düzeni gözden geçirildi", "Toplama yolu kısaltıldı"]} for i in range(count)]}

    assert deep_research._parse_slide_count("Depo verimliliği üzerine 3 slaytlık sunum hazırla.") == 2
    assert deep_research._slides_are_real(spec(2), "Depo verimliliği üzerine 3 slaytlık sunum hazırla.")
    assert not deep_research._slides_are_real(spec(1), "Depo verimliliği üzerine 3 slaytlık sunum hazırla.")
    assert not deep_research._slides_are_real(spec(2), "Depo verimliliği üzerine sunum hazırla.")
    assert deep_research._slides_are_real(spec(3), "Depo verimliliği üzerine sunum hazırla.")


def test_marked_values_never_reach_documents_logs_or_training_data(monkeypatch):
    import confidential
    import document_factory
    import log_sanitizer
    import security_scan

    store = {}
    monkeypatch.setattr(confidential.secret_store, "set_secret", store.__setitem__)
    monkeypatch.setattr(confidential.secret_store, "get_secret", lambda name: store.get(name, ""))
    monkeypatch.setattr(confidential.secret_store, "delete_secret", lambda name: store.pop(name, None))
    confidential._cache.clear()
    assert "işaretlendi" in confidential.observe("gizli işaretle: Mavi Fil Projesi")
    assert confidential.observe("Maaş listesi <gizli>Ayşe 85.000 TL</gizli> için özet yaz") == ""
    text = "mavi  fil\nprojesi bütçesi; AYŞE 85.000 TL alıyor."
    for sink in (security_scan.redact, log_sanitizer.redact_sensitive_text):
        out = sink(text)
        assert "fil" not in out.casefold() and "85.000" not in out and out.count(confidential.MASK) == 2, out
    content = document_factory._DocContent("Mavi Fil Projesi", "Ayşe 85.000 TL", [{"heading": "x", "content": "mavi fil projesi"}], ["a"], [["Ayşe 85.000 TL", 5]], "Türkçe")
    clean = confidential.scrub(content)
    assert confidential.MASK in clean.title and clean.rows == [[confidential.MASK, 5]] and "fil" not in str(clean.sections).casefold()
    assert "silindi" in confidential.observe("gizli verileri unut")
    assert security_scan.redact("mavi fil projesi") == "mavi fil projesi"
    confidential._cache.clear()


def test_a_branch_is_compared_with_its_origin_and_proofs_are_listed(tmp_path, monkeypatch):
    import json

    import config
    import run_api
    import run_evidence
    import workspace_builder as wb

    monkeypatch.setattr(config, "WORKSPACES_DIR", tmp_path)
    source = wb.safe_workspace_dir("asil")
    source.mkdir()
    (source / "a.py").write_text("x = 1\n", encoding="utf-8")
    wb.save_workspace_meta(source, {"id": "asil", "name": "Asil"})
    version = wb.create_snapshot(source, "ilk")["version"]
    branch = run_api.branch_workspace("asil", version)
    target = wb.safe_workspace_dir(branch["id"])
    (target / "a.py").write_text("x = 2\n", encoding="utf-8")
    (target / "yeni.py").write_text("y = 1\n", encoding="utf-8")
    result = run_evidence.compare_with_origin(branch["id"])
    assert [(f["path"], f["status"]) for f in result["files"]] == [("a.py", "değişti"), ("yeni.py", "eklendi")]
    assert "-x = 1" in result["files"][0]["diff"] and "+x = 2" in result["files"][0]["diff"]
    with pytest.raises(ValueError, match="dal değil"):
        run_evidence.compare_with_origin("asil")
    (target / ".ai-os").mkdir(exist_ok=True)
    (target / ".ai-os" / "proof.json").write_text(json.dumps({"proofs": {"A": ["geçti", "temiz"]}}), encoding="utf-8")
    (target / ".provenance.json").write_text(json.dumps({"warnings": ["Mutasyon testi: 8 hatanın 7'si yakalandı.", "başka bir not"]}), encoding="utf-8")
    shown = run_evidence.proofs(branch["id"])
    assert shown["stages"] == {"A": ["geçti", "temiz"]} and shown["evidence"] == ["Mutasyon testi: 8 hatanın 7'si yakalandı."]


def test_pareto_frontier_and_incident_report(tmp_path, monkeypatch):
    import config
    import release_history

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)

    def run(ok, total, seconds):
        return [{"name": f"s{i}", "ok": i < ok, "seconds": seconds, "note": "zaman aşımı" if i >= ok else ""} for i in range(total)]

    for ok, seconds, label in ((6, 30.0, "a"), (8, 60.0, "b"), (5, 45.0, "c")):
        release_history.add(run(ok, 10, seconds), label)
    assert [p["label"] for p in release_history.frontier(release_history.points())] == ["a", "b"]
    assert "sınırın gerisinde" in release_history.describe()
    text = release_history.incident(["s9"], run(9, 10, 1.0), ["agent_intake.md"], ["agent_intake.md"]).read_text(encoding="utf-8")
    assert "s9: zaman aşımı" in text and "- agent_intake.md" in text and "Geri alınan dosyalar: agent_intake.md" in text


def test_every_finished_file_of_a_change_carries_its_diff():
    import build_dag

    diff = build_dag.file_diff("a.js", "const a = 1;\nconst b = 2;\n", "const a = 1;\nconst b = 3;\n")
    assert "-const b = 2;" in diff and "+const b = 3;" in diff and "sonra/a.js" in diff
    assert build_dag.file_diff("a.js", "x", "x") == ""


def test_taste_is_learned_only_from_repeated_hand_edits(tmp_path, monkeypatch):
    import config
    import taste

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    old = "body { background: #ffffff; } .k { border-radius: 8px; color: red; } :root { --accent: #3b5bdb; }"
    new = "body { background: #0b0f14; } .k { border-radius: 2px; color: blue; } :root { --accent: #d9480f; }"
    assert dict(taste.added(old, new)) == {"köşe yuvarlaklığı": "2px", "ana renk": "#d9480f", "arka plan rengi": "#0b0f14"}
    assert taste.learn(old, new, ".py") == 0 and taste.learn(old, new, ".css") == 3
    assert taste.brief() == ""
    taste.learn(".a { color: red }", ".a { color: red; border-radius: 2px }", ".css")
    assert "köşe yuvarlaklığı: 2px (elle 2 kez" in taste.brief() and "ana renk" not in taste.brief()


def test_the_active_isolation_layer_is_named_honestly():
    import run_evidence

    assert "Docker kutusu" in run_evidence.isolation_tier(ready=lambda: (True, ""))
    assert "çalıştırılmıyor" in run_evidence.isolation_tier(ready=lambda: (False, ""), platform="win32")
    assert run_evidence.isolation_tier(ready=lambda: (False, ""), platform="linux").startswith("Yalıtım yok")
