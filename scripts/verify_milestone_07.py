"""v5 milestone 07 exit proof: ten real model edits in a row end with no architectural rot and no critical accessibility fault.

Usage: python scripts/verify_milestone_07.py      (exit 0 only when every check passes; needs Ollama and Chrome)
A small notes application is edited ten times through the platform's own follow-up flow. After every turn the fitness
guardian runs as it does for a user; at the end the project is scanned, opened in the browser and audited with axe-core.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_TMP = tempfile.mkdtemp(prefix="m07_")
os.environ.update(DB_PATH=str(Path(_TMP) / "veri" / "platform.db"), WORKSPACES_DIR=str(Path(_TMP) / "veri" / "workspaces"))
sys.path.insert(0, str(ROOT / "master"))

import a11y  # noqa: E402
import arch_heal  # noqa: E402
import arch_scan  # noqa: E402
import config  # noqa: E402
import torture_probe  # noqa: E402
import workspace_builder as wb  # noqa: E402

PROOF = ROOT / "eval" / "reports" / "milestone_07.json"
START = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Notlar</title>
<style>
body { font-family: system-ui, sans-serif; margin: 0; padding: 24px; background: #ffffff; color: #111827; }
main { max-width: 560px; margin: 0 auto; }
button { background: #1d4ed8; color: #ffffff; border: 0; border-radius: 6px; padding: 8px 14px; }
input { padding: 8px; border: 1px solid #6b7280; border-radius: 6px; }
li { margin: 6px 0; }
</style>
</head>
<body>
<main>
<h1>Notlar</h1>
<form id="form">
  <label for="note">Not</label>
  <input id="note" autocomplete="off">
  <button type="submit">Ekle</button>
</form>
<ul id="list"></ul>
</main>
<script>
const notes = [];
const list = document.getElementById('list');
function render() {
  list.replaceChildren(...notes.map(text => {
    const item = document.createElement('li');
    item.textContent = text;
    return item;
  }));
}
document.getElementById('form').addEventListener('submit', event => {
  event.preventDefault();
  const field = document.getElementById('note');
  const value = field.value.trim();
  if (!value) return;
  notes.push(value);
  field.value = '';
  render();
});
render();
</script>
</body>
</html>
"""
EDITS = (
    "Listenin üstüne toplam not sayısını gösteren bir yazı ekle.",
    "Her notun yanına 'Sil' düğmesi ekle.",
    "Notlar localStorage'da saklansın, sayfa yenilenince kaybolmasın.",
    "Notlarda arama yapan, etiketi olan bir arama kutusu ekle; Türkçe harfleri doğru eşleştirsin.",
    "Her nota 'yapıldı' onay kutusu ekle; yapılanların üstü çizili görünsün.",
    "'Tümü', 'Yapılacak' ve 'Yapılan' süzgeç düğmeleri ekle.",
    "'Tümünü sil' düğmesi ekle.",
    "Her notun eklendiği tarih ve saati göster.",
    "Boş not eklenmeye çalışılınca ekranda kısa bir uyarı yazısı göster.",
    "Koyu tema düğmesi ekle; koyu temada yazılar rahat okunsun.",
)


def code_tests() -> str:
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_v5_m07_fitness.py"], cwd=ROOT / "master",
                          env={**os.environ, "PYTHONPATH": "."}, capture_output=True, text=True, encoding="utf-8", timeout=600)  # noqa: S603, RUF100
    assert done.returncode == 0, done.stdout[-600:]
    return done.stdout.strip().splitlines()[-1]


def _page_errors(index: Path) -> list[str]:
    """Uncaught errors, and whether adding a note still works."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as driver:
        browser = driver.chromium.launch(channel="chrome")
        try:
            page = browser.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)[:160]))
            page.goto(index.as_uri())
            torture_probe.text_field(page).fill("kanıt notu 77")
            page.get_by_role("button", name="Ekle").first.click()
            page.wait_for_timeout(300)
            if "kanıt notu 77" not in page.inner_text("body"):
                errors.append("eklenen not görünmüyor")
            return errors
        finally:
            browser.close()


async def ten_edits() -> str:
    ws_dir = config.WORKSPACES_DIR / "m07-notlar"
    ws_dir.mkdir(parents=True)
    (ws_dir / "index.html").write_text(START, encoding="utf-8")
    wb.save_workspace_meta(ws_dir, {"id": ws_dir.name, "name": "Notlar", "project_type": "web", "entry_point": "index.html"})
    turns = []
    for number, instruction in enumerate(EDITS, 1):
        started, cleaned = time.time(), []
        async for event in wb.stream_iterate_project(ws_dir.name, instruction, os.environ.get("EDIT_MODEL") or "qwen3.5:9b"):
            if event.get("type") == "status" and any(word in event.get("message", "") for word in ("bölündü", "silindi", "alındı", "onarıldı", "uygulanmadı")):
                cleaned.append(event["message"])
        turn = {"turn": number, "seconds": round(time.time() - started), "findings": [f.line() for f in arch_scan.scan(ws_dir)], "cleaned": cleaned, "page_errors": await asyncio.to_thread(_page_errors, ws_dir / "index.html")}
        turns.append(turn)
        print(json.dumps(turn, ensure_ascii=False), flush=True)
    arch_heal.heal(ws_dir)  # the explicit clean-up at the end: nothing dead is left behind
    rot = [f.line() for f in arch_scan.scan(ws_dir)]
    faults = await asyncio.to_thread(a11y.audit, (ws_dir / "index.html").as_uri())
    assert faults is not None, "erişilebilirlik denetimi koşulamadı"
    critical = [line for line in faults if line.startswith("critical")]
    errors = await asyncio.to_thread(_page_errors, ws_dir / "index.html")
    (PROOF.parent / "milestone_07_page.html").write_text((ws_dir / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
    (PROOF.parent / "milestone_07_turns.json").write_text(json.dumps({"turns": turns, "rot": rot, "a11y": faults, "errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
    assert not rot and not critical and not errors, f"bozulma: {rot}\nkritik erişilebilirlik: {critical}\nsayfa hataları: {errors}"
    lines = (ws_dir / "index.html").read_text(encoding="utf-8").count("\n")
    return f"{len(EDITS)} düzenleme; {lines} satır; mimari bulgu 0, kritik erişilebilirlik 0, sayfa hatası 0" + (f"; ciddi uyarı: {len(faults)}" if faults else "")


def main() -> int:
    results = []

    def check(name: str, run) -> None:
        started = time.time()
        try:
            ok, detail = True, str(run())
        except Exception as exc:  # noqa: BLE001, RUF100  # any failure of a check is a failed check
            ok, detail = False, f"{type(exc).__name__}: {exc}"[:1500]
        results.append({"check": name, "ok": ok, "detail": detail, "seconds": round(time.time() - started, 1)})
        print(f"{'GEÇTİ' if ok else 'KALDI'} {name} ({results[-1]['seconds']} sn): {detail}", flush=True)

    PROOF.parent.mkdir(parents=True, exist_ok=True)
    check("kod testleri", code_tests)
    check("10 turluk gerçek düzenleme sonunda bozulma yok", lambda: asyncio.run(ten_edits()))
    PROOF.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(r["ok"] for r in results)
    print(f"{passed}/{len(results)} geçti | kanıt: {PROOF}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
