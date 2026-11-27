"""v5 milestone 02: repairs cannot game the checks, hollow work is found, and "done" needs four proofs."""

import itertools
import json

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
