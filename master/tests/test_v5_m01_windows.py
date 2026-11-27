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
