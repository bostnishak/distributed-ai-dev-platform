"""v5 milestone 02: repairs cannot game the checks, hollow work is found, and "done" needs four proofs."""

import itertools
import json
import sys

import pytest

import cheat_guard
import done_gate
import shortcut_audit
import workspace_smoke

pytestmark = pytest.mark.unit

_TEST = "from app import total\n\n\ndef test_total():\n    assert total([1, 2]) == 3\n    assert total([]) == 0\n\n\ndef test_speed():\n    assert total.cost < 100\n    assert total.accuracy >= 0.9\n"


@pytest.fixture
def data(tmp_path, monkeypatch):
    import config

    folder = tmp_path / "data"
    folder.mkdir()
    monkeypatch.setattr(config, "data_dir", lambda: folder)
    return folder


@pytest.mark.parametrize(("change", "reason"), [
    (_TEST.replace("    assert total([]) == 0\n", ""), "denetim sayısı"),
    (_TEST.replace("assert total([]) == 0", "assert True"), "her zaman doğru"),
    (_TEST.replace("assert total([]) == 0", "assert total([]) == total([])"), "her zaman doğru"),
    (_TEST.replace("def test_total", "@pytest.mark.skip\ndef test_total"), "atlatıldı"),
    (_TEST.replace("< 100", "< 100000"), "eşik gevşetildi"),
    (_TEST.replace(">= 0.9", ">= 0.1"), "eşik gevşetildi"),
    ("", "boşaltıldı"),
])
def test_every_way_of_weakening_a_test_is_rejected(change, reason):
    assert any(reason in v for v in cheat_guard.review("tests/test_app.py", _TEST, change)), cheat_guard.review("tests/test_app.py", _TEST, change)


def test_stronger_tests_and_honest_fixes_are_accepted():
    stronger = _TEST.replace("< 100", "< 50") + "\n\ndef test_more():\n    assert total([5]) == 5\n"
    assert cheat_guard.review("tests/test_app.py", _TEST, stronger) == []
    assert cheat_guard.review("app.py", "def total(x):\n    return 0\n", "def total(x):\n    return sum(x)\n", {"API Gateway Health Check"}) == []


def test_special_casing_a_test_value_and_touching_the_oracle_are_rejected():
    literals = cheat_guard.test_literals({"test_a.py": 'assert check("API Gateway Health Check") == "ok"'})
    cheating = 'def check(name):\n    if name == "API Gateway Health Check":\n        return "ok"\n    return probe(name)\n'
    assert any("koda gömüldü" in v for v in cheat_guard.review("app.py", "def check(name):\n    return probe(name)\n", cheating, literals))
    js = "function check(n){ if (n === 'API Gateway Health Check') return 'ok'; return probe(n) }"
    assert cheat_guard.review("app.js", "function check(n){ return probe(n) }", js, literals)
    assert "kehanet" in cheat_guard.review(".ai-os/oracles/spec.py", "x", "y")[0]


def test_a_cheating_repair_is_not_written_and_is_remembered(tmp_path, data):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "test_app.py").write_text(_TEST, encoding="utf-8")
    workspace_smoke._apply_fix(ws / "test_app.py", "```python\nfrom app import total\n\n\ndef test_total():\n    assert True\n```", ws)
    assert (ws / "test_app.py").read_text(encoding="utf-8") == _TEST
    entries = [json.loads(x) for x in (data / "cheats.jsonl").read_text(encoding="utf-8").splitlines()]
    assert entries and entries[0]["kind"] == "REWARD_HACK_ATTEMPT" and "TEKRARLAMA" in cheat_guard.guardrails()


def test_hollow_code_is_found_and_honest_code_is_not(tmp_path):
    (tmp_path / "app.py").write_text(
        "import time\nfrom fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/x')\ndef slow():\n    time.sleep(2)\n    return {'ok': True}\n\n"
        "def a():\n    try:\n        run()\n    except Exception:\n        return {}\n\ndef b():\n    try:\n        run()\n    except:\n        pass\n", encoding="utf-8")
    (tmp_path / "test_x.py").write_text("def test_nothing():\n    print('ok')\n\ndef test_true():\n    assert True\n", encoding="utf-8")
    (tmp_path / "app.js").write_text("try { save() } catch (e) {}\nbtn.onclick = () => setTimeout(() => { out.textContent = 'Başarıyla kaydedildi' }, 900)\n", encoding="utf-8")
    found = "\n".join(shortcut_audit.findings(tmp_path))
    for expected in ("yapay bekleme (slow)", "app.py:13", "app.py:19", "boş catch", "uydurma sonuç", "test_nothing", "test_true"):
        assert expected in found, found
    for path in tmp_path.iterdir():
        path.unlink()
    (tmp_path / "ok.py").write_text("import logging\n\ndef a():\n    try:\n        run()\n    except ValueError as exc:\n        logging.warning(exc)\n        return {}\n", encoding="utf-8")
    (tmp_path / "ok.js").write_text("try { save() } catch (e) { show(e.message) }\nsetTimeout(() => hideToast(), 3000)\n", encoding="utf-8")
    assert shortcut_audit.findings(tmp_path) == []


def test_completed_is_unreachable_without_four_passed_proofs():
    statuses = (done_gate.PASSED, done_gate.FAILED, done_gate.MISSING)
    for combination in itertools.product(statuses, repeat=4):
        delivery = done_gate.Delivery()
        assert delivery.state == "BUILDING"
        for stage, status in zip(done_gate.STAGES, combination, strict=True):
            delivery.prove(stage, status, "x")
        assert (delivery.state == "COMPLETED") == (set(combination) == {done_gate.PASSED})
        assert ("TAMAMLANDI" in delivery.summary()) == (delivery.state == "COMPLETED")
    with pytest.raises(ValueError, match="sıra dışı"):
        done_gate.Delivery().prove("C", done_gate.PASSED, "x")


def test_a_real_page_with_a_dead_button_or_an_error_fails_the_live_proof(tmp_path):
    pytest.importorskip("playwright")
    page = tmp_path / "index.html"
    page.write_text("<meta charset='utf-8'><h1>Liste</h1><button id=a>Ekle</button><button id=b>Süs</button>"
                    "<form onsubmit='return false'><button>Gönder</button></form><script>document.getElementById('a').addEventListener('click',()=>1)</script>", encoding="utf-8")
    status, detail = done_gate.page_problems(page.as_uri())
    if status == done_gate.MISSING:
        pytest.skip(detail)
    assert status == done_gate.FAILED and "Süs" in detail and "Ekle" not in detail and "Gönder" not in detail, detail
    page.write_text("<meta charset='utf-8'><h1>Liste</h1><button onclick='this.textContent=1'>Ekle</button>", encoding="utf-8")
    assert done_gate.page_problems(page.as_uri())[0] == done_gate.PASSED
    page.write_text("<meta charset='utf-8'><h1>x</h1><script>missing()</script>", encoding="utf-8")
    assert "sayfa hatası" in done_gate.page_problems(page.as_uri())[1]


def test_a_delivery_without_tests_says_so_and_writes_a_signed_record(tmp_path, data, monkeypatch):
    ws = tmp_path / "proje-1"
    ws.mkdir()
    (ws / "index.html").write_text("<h1>x</h1>", encoding="utf-8")
    monkeypatch.setattr(done_gate, "live_proof", lambda *_a: (done_gate.PASSED, "tamam"))
    delivery = done_gate.evaluate(ws, [])
    assert delivery.state == "INCOMPLETE_WITH_DIAGNOSTICS" and delivery.proofs["B"][0] == done_gate.MISSING
    assert "tamamlandı sayılmaz" in delivery.summary()
    record = json.loads((ws / done_gate.RECORD).read_text(encoding="utf-8"))
    assert len(record["signature"]) == 128 and "index.html" in record["files"]
    assert not any(f.startswith(".ai-os") for f in done_gate.wb.list_relative_files(ws))


def test_a_missing_browser_is_not_reported_as_a_broken_page(tmp_path, monkeypatch):
    pytest.importorskip("playwright")
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "yok"))
    with sync_playwright() as driver:
        try:
            driver.chromium.launch().close()
            pytest.skip("tarayıcı yolu değiştirilemedi")
        except PlaywrightError as exc:  # confirms the launch really fails here
            assert "Executable" in str(exc)
    status, detail = done_gate.page_problems((tmp_path / "x.html").as_uri())
    assert status == done_gate.MISSING and "tarayıcı açılamadı" in detail


def test_oracle_is_written_once_and_missing_endpoints_are_named(tmp_path):
    import plan_matrix

    plan_matrix.write_oracle(tmp_path, {"endpoints": [{"method": "post", "path": "/api/notlar"}, {"method": "delete", "path": "/api/notlar/:id"}]})
    plan_matrix.write_oracle(tmp_path, {"endpoints": []})  # a later step cannot lower the bar
    openapi = {"paths": {"/api/notlar/": {"post": {}}, "/api/notlar/{not_id}": {"get": {}}}}
    assert plan_matrix.missing_endpoints(tmp_path, openapi) == ["DELETE /api/notlar/:id"]
    openapi["paths"]["/api/notlar/{not_id}"]["delete"] = {}
    assert plan_matrix.missing_endpoints(tmp_path, openapi) == []


def test_static_proof_stops_on_compiler_errors_and_unsafe_code(tmp_path):
    import done_gate

    (tmp_path / "main.py").write_text("import os\n\n\ndef run(komut):\n    os.system('echo ' + komut)\n    return tanimsiz_ad\n", encoding="utf-8")
    status, detail = done_gate.static_proof(tmp_path)
    assert status == done_gate.FAILED and "tanimsiz_ad" in detail, detail
    assert any("main.py:5" in part for part in detail.split("; ")), detail


def test_a_rejected_shortcut_becomes_a_memory_rule(tmp_path, monkeypatch):
    import cheat_guard
    import config
    import memory_engine

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(memory_engine, "_memory_db_path", lambda: tmp_path / "m.db")
    cheat_guard.record(["tests/test_a.py: assert silindi"])
    cheat_guard.record(["tests/test_a.py: assert silindi"])
    rules = [f for f in memory_engine.list_semantic_facts() if f["category"] == "guardrail"]
    assert len(rules) == 1 and "assert silindi" in rules[0]["fact_value"]


def test_fields_nothing_listens_to_are_reported(tmp_path):
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import Error, sync_playwright

    import shortcut_audit

    page_file = tmp_path / "a.html"
    page_file.write_text("<select aria-label='bos'><option>1</option></select><input id='ad'><input aria-label='olu'>"
                         "<form><input name='x'></form><script>document.getElementById('ad').value = 'a';</script>", encoding="utf-8")
    with sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except Error:
            pytest.skip("tarayıcı yok")
        page = browser.new_page()
        page.goto(page_file.as_uri())
        found = shortcut_audit.unwired(page)
        browser.close()
    assert found == ["alan: bos", "alan: olu"], found


def test_javascript_mutation_finds_weak_tests_in_a_run_that_cannot_write_or_connect(tmp_path):
    import shutil

    import done_gate
    import js_mutation

    pytest.importorskip("tree_sitter_javascript")
    if not shutil.which("node") or sys.platform != "win32":
        pytest.skip("node ya da Windows yok")
    (tmp_path / "hesap.js").write_text("function indirim(tutar) {\n  if (tutar >= 100) {\n    return tutar - 10;\n  }\n  return tutar;\n}\nmodule.exports = { indirim };\n", encoding="utf-8")
    test = tmp_path / "hesap.test.js"
    test.write_text("const assert = require('assert');\nconst { indirim } = require('./hesap.js');\nassert.ok(indirim(500) < 500);\n", encoding="utf-8")
    tried, survived = js_mutation.run(tmp_path)
    assert tried >= 3 and survived, (tried, survived)
    assert done_gate.test_proof(tmp_path)[0] == done_gate.FAILED
    test.write_text("const assert = require('assert');\nconst { indirim } = require('./hesap.js');\n"
                    "assert.strictEqual(indirim(100), 90);\nassert.strictEqual(indirim(99), 99);\nassert.strictEqual(indirim(101), 91);\n", encoding="utf-8")
    status, detail = done_gate.test_proof(tmp_path)
    assert status == done_gate.PASSED, detail
    for attack in ("require('fs').writeFileSync('x.txt', 'a')", "require('child_process').execSync('whoami')", "require('fs').readFileSync('C:/Windows/win.ini')",
                   "require('net').connect(80, '1.1.1.1').on('error', e => { throw e })"):
        test.write_text(attack + ";\n", encoding="utf-8")
        assert "ERR_ACCESS_DENIED" in js_mutation.run_tests(tmp_path), attack
    assert not (tmp_path / "x.txt").exists()


def test_data_flow_between_functions_none_access_and_dead_code(tmp_path):
    import flow_analysis

    (tmp_path / "araclar.py").write_text("import os\n\n\ndef calistir(komut):\n    metin = 'ping ' + komut\n    os.system(metin)\n\n\n"
                                         "def ara(db, ad):\n    db.execute(f\"SELECT * FROM k WHERE ad = '{ad}'\")\n\n\n"
                                         "def bul(liste, ad):\n    for x in liste:\n        if x == ad:\n            return x\n    return None\n\n\ndef kimse_cagirmiyor():\n    return 1\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("from araclar import ara, bul, calistir\n\n\n@app.get('/p')\ndef ping(host: str):\n    calistir(host)\n\n\n"
                                      "@app.get('/s')\ndef sorgu(ad: str):\n    ara(db, ad)\n    sonuc = bul([], ad)\n    return sonuc.upper()\n\n\n"
                                      "@app.get('/g')\ndef guvenli(sayi: str):\n    adet = int(sayi)\n    calistir(str(adet))\n    kayit = bul([], 'a')\n    if kayit:\n        return kayit.upper()\n", encoding="utf-8")
    flows = " | ".join(flow_analysis.tainted_flows(tmp_path))
    assert "os.system" in flows and "ping -> calistir" in flows and "SQL metni" in flows and "sorgu -> ara" in flows, flows
    assert "guvenli" not in flows
    nones = flow_analysis.none_accesses(tmp_path)
    assert len(nones) == 1 and "sonuc None olabilir" in nones[0], nones
    assert [d.split()[1] for d in flow_analysis.dead_functions(tmp_path)] == ["kimse_cagirmiyor"]


def test_submissions_never_run_in_the_platform_and_cannot_see_the_answers():
    import ast
    from pathlib import Path

    import autograder
    import education_and_domains

    sent = []

    def fake(script):
        sent.append(script)
        marker = next(line for line in script.splitlines() if line.startswith("print(")).split("'")[1]
        return {"docker_available": True, "stdout": "baska cikti\n" + marker + '{"defined": true, "results": [{"got": 5}, {"error": "ZeroDivisionError"}]}'}

    cases = [{"args": [2, 3], "expected": 5}, {"args": [1, 0], "expected": 987654321}]
    result = autograder.grade("def f(a, b):\n    return a + b\n", "f", cases, run=fake)
    assert result["score"] == 50.0 and not result["passed"] and "987654321" not in sent[0]
    assert "Docker" in autograder.grade("x = 1", "f", cases, run=lambda _s: {"docker_available": False})["error"]
    source = Path(education_and_domains.__file__).read_text(encoding="utf-8")
    assert not [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call) and getattr(n.func, "id", "") in ("exec", "eval")]


def test_a_real_escape_attempt_stays_inside_the_container():
    import autograder
    from sandbox import runner

    if not runner.docker_daemon_ready()[0]:
        pytest.skip("Docker kapalı")
    attack = ("def f():\n    import os, socket\n    found = [c for c in ().__class__.__base__.__subclasses__() if c.__name__ == 'Popen']\n"
              "    try:\n        socket.create_connection(('1.1.1.1', 80), timeout=3)\n        net = 'ag acik'\n    except OSError:\n        net = 'ag yok'\n"
              "    try:\n        open('/sandbox/x', 'w').write('a')\n        disk = 'yazdi'\n    except OSError:\n        disk = 'salt okunur'\n"
              "    return [os.name, os.getuid(), net, disk]\n")
    result = autograder.grade(attack, "f", [{"args": [], "expected": ["posix", 10001, "ag yok", "salt okunur"]}])
    assert result["passed"], result


def test_a_benchmark_answer_from_another_machine_never_runs_on_this_one(tmp_path):
    import benchmarks
    from sandbox import runner

    benchmark = next(b for b in benchmarks.BENCHMARKS if b["dimension"] == "coding")
    escape = tmp_path / "ele-gecirildi.txt"
    hostile = f"import pathlib\npathlib.Path({str(escape)!r}).write_text('x')\n"
    score, details = benchmarks.score_response(benchmark, hostile)
    assert score == 0 and not escape.exists() and details["error"], details
    if not runner.docker_daemon_ready()[0]:
        assert "not available" in details["error"]
