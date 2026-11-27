"""v5 milestone 08 exit proof: a dashboard with charts, diagrams and maths works with the network completely cut.

Usage: python scripts/verify_milestone_08.py      (exit 0 only when every check passes; needs Chrome, uses Ollama when MODEL=1)
The page is written the way models write it (CDN links), passed through the platform's vault step, exported as ZIP,
unpacked elsewhere and opened in a browser whose every network request is refused.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_TMP = tempfile.mkdtemp(prefix="m08_")
os.environ.update(DB_PATH=str(Path(_TMP) / "veri" / "platform.db"), WORKSPACES_DIR=str(Path(_TMP) / "veri" / "workspaces"))
sys.path.insert(0, str(ROOT / "master"))

import asset_vault  # noqa: E402
import config  # noqa: E402
import docs_index  # noqa: E402
import studio_api  # noqa: E402
import workspace_builder as wb  # noqa: E402
import workspace_requirements  # noqa: E402

PROOF = ROOT / "eval" / "reports" / "milestone_08.json"
DASHBOARD = """<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Üretim panosu</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter&family=JetBrains+Mono&family=Plus+Jakarta+Sans&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script><script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.30.0/cytoscape.min.js"></script>
<style>body{font-family:'Inter',sans-serif;margin:16px}h1{font-family:'Plus Jakarta Sans',sans-serif}code{font-family:'JetBrains Mono',monospace}#graph{width:400px;height:200px}.box{max-width:600px}</style></head>
<body><h1>Üretim panosu: İğne ve şişe hattı</h1><p><code>ğüşİı 0123456789</code></p><div class="box"><canvas id="chart"></canvas></div><div id="math"></div><div id="graph"></div>
<pre class="mermaid">flowchart LR
  A[Giriş] --> B{Kalite}
  B -->|uygun| C[Depo]
  B -->|hatalı| D[Yeniden işle]</pre>
<script>
new Chart(document.getElementById('chart'), {type: 'bar', data: {labels: ['Oca', 'Şub', 'Mar'], datasets: [{label: 'Adet', data: [120, 190, 150]}]}, options: {animation: false}});
katex.render('\\\\bar{x} = \\\\frac{1}{n}\\\\sum_{i=1}^{n} x_i', document.getElementById('math'));
cytoscape({container: document.getElementById('graph'), elements: [{data: {id: 'a'}}, {data: {id: 'b'}}, {data: {source: 'a', target: 'b'}}], layout: {name: 'grid'}});
</script>
<script type="module">import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs'; mermaid.initialize({startOnLoad: true});</script>
</body></html>"""
_PROBE = """async () => {
  await document.fonts.ready;
  await Promise.all(["16px Inter", "16px 'Plus Jakarta Sans'", "16px 'JetBrains Mono'"].map(f => document.fonts.load(f, 'ğİşA')));
  const canvas = document.getElementById('chart');
  const pixels = canvas ? canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data : [];
  return {
    painted: Array.from(pixels).filter((v, i) => i % 4 === 3 && v > 0).length,
    mermaid: document.querySelectorAll('.mermaid svg .node').length,
    katex: document.querySelectorAll('#math .katex').length,
    graph: document.querySelectorAll('#graph canvas').length,
    fonts: [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/["']/g, '')),
  };
}"""


def code_tests() -> str:
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_v5_m08_vault.py"], cwd=ROOT / "master",
                          env={**os.environ, "PYTHONPATH": "."}, capture_output=True, text=True, encoding="utf-8", timeout=600)  # noqa: S603, RUF100
    assert done.returncode == 0, done.stdout[-600:]
    return done.stdout.strip().splitlines()[-1]


def open_offline(index: Path, wait_for: str) -> tuple[dict, list[str], list[str]]:
    """(page measurements, console errors, refused or failed requests) with every non-file request aborted."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as driver:
        browser = driver.chromium.launch(channel="chrome", args=["--allow-file-access-from-files"])
        try:
            context = browser.new_context()
            refused: list[str] = []
            context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(("file:", "data:", "blob:")) else (refused.append(route.request.url), route.abort()))
            page = context.new_page()
            errors: list[str] = []
            page.on("console", lambda message: errors.append(message.text[:200]) if message.type == "error" else None)
            page.on("pageerror", lambda error: errors.append(str(error)[:200]))
            page.on("requestfailed", lambda request: refused.append(request.url))
            page.goto(index.as_uri())
            if wait_for:
                page.wait_for_selector(wait_for, timeout=20000)
            page.wait_for_timeout(800)
            measured = page.evaluate(_PROBE)
            page.screenshot(path=str(PROOF.parent / "milestone_08_offline.png"), full_page=True)
            return measured, errors, refused
        finally:
            browser.close()


async def _zip_bytes(ws_id: str) -> bytes:
    response = await studio_api.download_workspace_zip(ws_id)
    return b"".join([chunk async for chunk in response.body_iterator])


def exported_dashboard_offline() -> str:
    ws_dir = config.WORKSPACES_DIR / "m08-pano"
    ws_dir.mkdir(parents=True)
    (ws_dir / "index.html").write_text(DASHBOARD, encoding="utf-8")
    workspace_requirements.repair_project(ws_dir)  # the same step every build and edit goes through
    left = asset_vault.external(ws_dir)
    assert not left, f"dış bağlantı kaldı: {left}"
    unpacked = Path(_TMP) / "baska-yer"
    zipfile.ZipFile(io.BytesIO(asyncio.run(_zip_bytes(ws_dir.name)))).extractall(unpacked)  # our own export
    measured, errors, refused = open_offline(unpacked / ws_dir.name / "index.html", ".mermaid svg")
    assert not errors and not refused, f"konsol: {errors[:3]} ağ: {refused[:3]}"
    assert measured["painted"] > 500 and measured["mermaid"] >= 4 and measured["katex"] == 1 and measured["graph"] >= 1, str(measured)
    missing = {"Inter", "Plus Jakarta Sans", "Jetbrains Mono"} - set(measured["fonts"])
    assert not missing, f"yüklenmeyen yazı tipi: {missing} (yüklenen {measured['fonts']})"
    return f"grafik {measured['painted']} piksel, diyagramda {measured['mermaid']} düğüm, formül ve ağ çizimi var, 3 yazı tipi yüklendi; konsol hatası 0, ağ isteği 0"


def unlisted_library_is_reported() -> str:
    ws_dir = config.WORKSPACES_DIR / "m08-red"
    ws_dir.mkdir(parents=True)
    (ws_dir / "index.html").write_text('<script src="https://cdn.tailwindcss.com"></script><p>x</p>', encoding="utf-8")
    import done_gate

    status, detail = done_gate.live_proof(ws_dir, [])
    assert status == done_gate.FAILED and "tailwind" in detail, f"{status} {detail}"
    return detail


def offline_documentation() -> str:
    pages = docs_index.build()
    assert pages > 1000, f"belge indeksi boş ({pages}); scripts/vendor_fetch.py --docs-only çalıştırılmalı"
    started = time.perf_counter()
    hit = docs_index.search("write-ahead logging checkpoint", ("sqlite",), 1)
    assert hit and "wal" in hit[0][1].lower(), str([h[:3] for h in hit])
    return f"{pages} sayfa indekslendi; arama {1000 * (time.perf_counter() - started):.0f} ms: {hit[0][2]}"


async def generated_by_model() -> str:
    """A model writes the dashboard itself; whatever it links to must still work offline."""
    request = ("Tek sayfalık bir satış panosu yap: tek HTML dosyası, Chart.js ile aylık satış çubuk grafiği (Oca 12, Şub 19, Mar 15) ve "
               "Mermaid ile 'Sipariş -> Hazırlık -> Kargo' akış diyagramı olsun. Kütüphaneleri CDN adresinden yükle.")
    done = {}
    async for event in wb.stream_generate_project(request, run_smoke=False):
        done = event if event.get("type") == "done" else done
    ws_dir = wb.safe_workspace_dir(done["workspace"]["id"])
    left = asset_vault.external(ws_dir)
    assert not left, f"dış bağlantı kaldı: {left}"
    measured, errors, refused = open_offline(ws_dir / "index.html", "")
    (PROOF.parent / "milestone_08_generated.html").write_text((ws_dir / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
    canvases = (ws_dir / "index.html").read_text(encoding="utf-8").count("<canvas")
    assert not errors and not refused, f"konsol: {errors[:3]} ağ: {refused[:3]}"
    assert canvases >= 1, "grafik alanı yok"
    return f"model üretimi pano çevrimdışı hatasız açıldı ({canvases} grafik alanı, {measured['mermaid']} diyagram düğümü)"


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
    check("ZIP'ten açılan pano ağ kesikken çalışır", exported_dashboard_offline)
    check("kasada olmayan kütüphane teslimi engeller", unlisted_library_is_reported)
    check("çevrimdışı belge indeksi", offline_documentation)
    if os.environ.get("MODEL") == "1":
        check("modelin ürettiği pano çevrimdışı çalışır", lambda: asyncio.run(generated_by_model()))
    PROOF.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(r["ok"] for r in results)
    print(f"{passed}/{len(results)} geçti | kanıt: {PROOF}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
