"""v5 milestone 14 exit proof: the glass box in a real browser, and a server killed mid-build that resumes cleanly.

Usage: master/venv/Scripts/python.exe scripts/verify_milestone_14.py      (needs Ollama, Chrome)
A real server on its own data folder; the build is a real model run; the process is killed after the first file.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
_TMP = Path(tempfile.mkdtemp(prefix="m14_"))
PROOF = ROOT / "eval" / "reports" / "milestone_14.json"
ENV = {**os.environ, "DB_PATH": str(_TMP / "veri" / "platform.db"), "WORKSPACES_DIR": str(_TMP / "veri" / "workspaces"), "PYTHONIOENCODING": "utf-8"}
BUILD = "Ayrı dosyalarla (index.html, css/styles.css, js/app.js, README.md) küçük bir alışveriş listesi web sayfası yap."


def _port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


PORT, PREVIEW = _port(), _port()
ENV["PREVIEW_PORT"] = str(PREVIEW)
BASE = f"http://127.0.0.1:{PORT}"


def start() -> subprocess.Popen:
    log = (_TMP / "server.log").open("a", encoding="utf-8")
    process = subprocess.Popen([sys.executable, "-X", "utf8", "-m", "uvicorn", "app:app", "--app-dir", str(ROOT / "master"), "--host", "127.0.0.1", "--port", str(PORT)],  # noqa: S603, RUF100
                               cwd=ROOT / "master", env=ENV, stdout=log, stderr=log)
    for _ in range(120):
        time.sleep(0.5)
        try:
            if httpx.get(f"{BASE}/health", timeout=2).status_code == 200:
                return process
        except httpx.HTTPError:
            continue
    raise AssertionError((_TMP / "server.log").read_text(encoding="utf-8")[-600:])


def kill(process: subprocess.Popen) -> None:
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)  # noqa: S603, S607, RUF100
    process.wait(timeout=30)


def code_tests() -> str:
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_v5_m14_glass.py"], cwd=ROOT / "master",
                          env={**os.environ, "PYTHONPATH": "."}, capture_output=True, text=True, encoding="utf-8", timeout=600)  # noqa: S603, RUF100
    assert done.returncode == 0, done.stdout[-600:]
    return done.stdout.strip().splitlines()[-1]


def _chat(prompt: str, events: list[dict], stop: threading.Event) -> None:
    with httpx.stream("POST", f"{BASE}/api/assistant/chat/stream", files={"prompt": (None, prompt)}, timeout=1500) as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
            if stop.is_set():
                return


def interrupted_build_resumes() -> str:
    server = start()
    events: list[dict] = []
    stop = threading.Event()
    worker = threading.Thread(target=lambda: _swallow(_chat, BUILD, events, stop), daemon=True)
    worker.start()
    latencies: list[float] = []
    try:
        deadline = time.time() + 900
        while time.time() < deadline and not _written():
            began = time.perf_counter()
            assert httpx.get(f"{BASE}/api/glass/hardware", timeout=10).status_code == 200
            latencies.append(time.perf_counter() - began)
            assert worker.is_alive() or _written(), f"üretim erken bitti: {events[-3:]}"
            time.sleep(1)
        assert _written(), "hiç dosya yazılmadı"
    finally:
        kill(server)  # the machine "shuts down" in the middle of the build
        stop.set()
    server = start()
    try:
        waiting = httpx.get(f"{BASE}/api/glass/unfinished", timeout=30).json()["unfinished"]
        assert waiting, "yarım kalan proje listelenmedi"
        resumed: list[dict] = []
        _chat("devam et", resumed, threading.Event())
        assert any(e.get("type") == "workspace" for e in resumed), str(resumed[-3:])[:600]
        after = httpx.get(f"{BASE}/api/glass/unfinished", timeout=30).json()["unfinished"]
        assert not after, f"hâlâ yarım görünüyor: {after}"
        ws_id = waiting[0]["id"]
        files = httpx.get(f"{BASE}/api/studio/workspaces/{ws_id}/tree", timeout=30).text
    finally:
        kill(server)
    assert all(name in files for name in ("index.html", "app.js", "styles.css")), files[:600]
    slowest = max(latencies) if latencies else 0.0
    assert slowest < 3.0, f"üretim sürerken arayüz isteği {slowest:.1f} sn bekledi"
    return (f"{waiting[0]['done']}/{waiting[0]['total']} dosyada sunucu öldürüldü; yeniden açılınca listelendi ve `devam et` ile tamamlandı; "
            f"üretim sürerken {len(latencies)} gösterge isteğinin en yavaşı {slowest * 1000:.0f} ms")


def _written() -> bool:
    for marker in (_TMP / "veri" / "workspaces").glob("*/.checkpoint.json"):
        try:
            if json.loads(marker.read_text(encoding="utf-8")).get("done"):
                return True
        except (OSError, ValueError):
            continue
    return False


def _swallow(function, *args) -> None:
    try:
        function(*args)
    except (httpx.HTTPError, ValueError, OSError):
        return  # the server is killed under this request on purpose


def glass_box_in_a_browser() -> str:
    ws_root = _TMP / "veri" / "workspaces"
    server = start()
    try:
        ws_id = next(p.name for p in ws_root.iterdir() if (p / "index.html").is_file())
        page_file = ws_root / ws_id / "index.html"
        original = page_file.read_text(encoding="utf-8")
        sys.path.insert(0, str(ROOT / "master"))
        os.environ.update({k: ENV[k] for k in ("DB_PATH", "WORKSPACES_DIR")})
        import done_gate
        import glass_box
        import workspace_builder as wb

        done_gate.evaluate(wb.safe_workspace_dir(ws_id), [])
        glass_box.snapshot_before(wb.safe_workspace_dir(ws_id), "kanıt değişikliği")
        page_file.write_text(original.replace("<body", "<body data-degisti", 1), encoding="utf-8")
        from playwright.sync_api import sync_playwright

        with sync_playwright() as driver:
            browser = driver.chromium.launch(channel="chrome")
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(BASE)
            page.wait_for_selector(".hw-ribbon .hw-item", timeout=30000)
            ribbon = page.inner_text(".hw-ribbon")
            script = ("async (id) => { const m = await import('/static/js/assistant_ide_card.js'); const t = await (await fetch(`/api/studio/workspaces/${id}/tree`)).json();"
                      " document.body.append(m.buildInlineWorkspaceCard({id, name: id, has_web_preview: true, entry_point: 'index.html'}, t.tree || t)); }")
            page.evaluate(script, ws_id)
            card = page.locator(".glass-bar").last
            card.get_by_role("button", name="Canlı kanıt").click()
            page.wait_for_selector(".proof-marks li", timeout=30000)
            marks = page.locator(".proof-marks li").all_inner_texts()
            shots = page.locator(".proof-film img").count()
            card.get_by_role("button", name="Geri al").click()
            page.wait_for_function("document.querySelector('.glass-note').textContent.includes('Geri alındı')", timeout=15000)
            note = page.inner_text(".glass-note")
            # reopen: the open tab and the view come back
            page.locator(".ide-mode-btn", has_text="</> Kod").last.click()
            page.wait_for_timeout(300)
            saved = page.evaluate("id => localStorage.getItem('ide-tabs:' + id)", ws_id)
            page.screenshot(path=str(PROOF.parent / "milestone_14_glass.png"))
            browser.close()
    finally:
        kill(server)
    assert "VRAM" in ribbon and "RAM" in ribbon and "Yalıtım" in ribbon, ribbon
    assert page_file.read_text(encoding="utf-8") == original, "geri alma dosyayı eski hâline getirmedi"
    assert any("geçti" in m or "kaldı" in m for m in marks) and shots >= 1, f"{marks} {shots}"
    assert saved and '"view":"code"' in saved and not errors, f"{saved} {errors}"
    return f"şerit: {' | '.join(ribbon.split(chr(10))[:3])}; {len(marks)} işaret, {shots} ekran görüntüsü; {note}; sekme durumu saklandı"


def main() -> int:
    results = []

    def check(name: str, run) -> None:
        started = time.time()
        try:
            ok, detail = True, str(run())
        except Exception as exc:  # noqa: BLE001, RUF100  # any failure of a check is a failed check
            ok, detail = False, f"{type(exc).__name__}: {exc}"[:900]
        results.append({"check": name, "ok": ok, "detail": detail, "seconds": round(time.time() - started, 1)})
        print(f"{'GEÇTİ' if ok else 'KALDI'} {name} ({results[-1]['seconds']} sn): {detail}", flush=True)

    PROOF.parent.mkdir(parents=True, exist_ok=True)
    check("kod testleri", code_tests)
    check("yarıda kapanan üretim devam eder, arayüz donmaz", interrupted_build_resumes)
    check("cam kutu gerçek tarayıcıda", glass_box_in_a_browser)
    PROOF.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(r["ok"] for r in results)
    print(f"{passed}/{len(results)} geçti | kanıt: {PROOF}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
