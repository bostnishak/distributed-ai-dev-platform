"""v5 milestone 12 exit proof: a model-generated app is exported, unpacked elsewhere, started by its own script and used.

Usage: master/venv/Scripts/python.exe scripts/verify_milestone_12.py      (needs Ollama, Docker, Chrome and network)
The model-generated project boots only inside a container. The kit's run.ps1 is additionally run on the host for a
small application written here (trusted code), the way a user would double-click it.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
_TMP = tempfile.mkdtemp(prefix="m12_")
os.environ.update(DB_PATH=str(Path(_TMP) / "veri" / "platform.db"), WORKSPACES_DIR=str(Path(_TMP) / "veri" / "workspaces"))
sys.path.insert(0, str(ROOT / "master"))
sys.path.insert(0, str(ROOT / "master" / "tests"))

import config  # noqa: E402
import doc_drift  # noqa: E402
import portable_kit  # noqa: E402
import workspace_builder as wb  # noqa: E402
from test_v5_m12_packaging import APP  # noqa: E402

PROOF = ROOT / "eval" / "reports" / "milestone_12.json"
REQUEST = "FastAPI ve SQLite ile tek dosyalık (app.py) bir kitap listesi yap: GET ve POST /api/kitaplar, ana sayfada basit bir liste; README.md ve requirements.txt olsun."


def code_tests() -> str:
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_v5_m12_packaging.py"], cwd=ROOT / "master",
                          env={**os.environ, "PYTHONPATH": "."}, capture_output=True, text=True, encoding="utf-8", timeout=600)  # noqa: S603, RUF100
    assert done.returncode == 0, done.stdout[-600:]
    return done.stdout.strip().splitlines()[-1]


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def kit_script_on_host() -> str:
    """ZIP -> empty folder -> run.ps1 builds its own virtual environment, installs and starts; then a real browser."""
    ws_dir = config.WORKSPACES_DIR / "m12-notlar"
    ws_dir.mkdir(parents=True)
    (ws_dir / "app.py").write_text(APP, encoding="utf-8")
    (ws_dir / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")
    copy = portable_kit.unpack(portable_kit.archive(ws_dir, "notlar"), Path(tempfile.mkdtemp(prefix="m12_acilan_")))
    port, log = _free_port(), Path(_TMP) / "run.log"
    started = time.time()
    with log.open("w", encoding="utf-8") as out:
        process = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(copy / "run.ps1"), "-Port", str(port), "-NoBrowser"],  # noqa: S603, S607, RUF100
                                   cwd=_TMP, stdout=out, stderr=out)
        try:
            while f"HAZIR http://127.0.0.1:{port}" not in log.read_text(encoding="utf-8", errors="replace"):
                assert process.poll() is None and time.time() - started < 600, log.read_text(encoding="utf-8", errors="replace")[-600:]
                time.sleep(2)
            assert httpx.post(f"http://127.0.0.1:{port}/api/notlar", params={"metin": "kanıt"}, timeout=10).status_code == 201
            assert httpx.get(f"http://127.0.0.1:{port}/api/notlar", timeout=10).status_code == 200
            from playwright.sync_api import sync_playwright

            with sync_playwright() as driver:
                browser = driver.chromium.launch(channel="chrome")
                page = browser.new_page()
                errors: list[str] = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{port}/")
                shown = page.inner_text("body")
                browser.close()
            assert "Notlar hazır" in shown and not errors, f"{shown} {errors}"
        finally:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)  # noqa: S603, S607, RUF100
    return f"run.ps1 {round(time.time() - started)} sn'de sanal ortam kurup başlattı; HTTP 201/200 ve sayfa hatasız (bağımlılık: {(copy / 'requirements.lock').read_text().split()[:2]})"


async def _generate() -> Path:
    done = {}
    import project_flow

    async for event in project_flow.stream_generate(REQUEST):
        done = event if event.get("type") == "done" else done
    return wb.safe_workspace_dir(done["workspace"]["id"])


def generated_app_exported() -> str:
    ws_dir = asyncio.run(_generate())
    (PROOF.parent / "milestone_12_readme.md").write_text((ws_dir / "README.md").read_text(encoding="utf-8") if (ws_dir / "README.md").is_file() else "", encoding="utf-8")
    drift = doc_drift.lines(ws_dir)
    assert not drift, f"README gerçek koddan sapmış: {drift[:4]}"
    passed, detail = portable_kit.docker_test(ws_dir)
    assert passed, detail
    return f"modelin ürettiği {ws_dir.name}: README koda uyuyor; {detail}"


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
    check("ZIP boş klasörde kendi betiğiyle açılır", kit_script_on_host)
    check("modelin ürettiği uygulama dışa aktarılıp kapta açılır", generated_app_exported)
    PROOF.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(r["ok"] for r in results)
    print(f"{passed}/{len(results)} geçti | kanıt: {PROOF}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
