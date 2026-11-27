"""v5 milestone 03 exit proof: a real full-stack application must survive a hard reload and a server restart.

Usage: python scripts/verify_milestone_03.py      (exit 0 only when every check passes)
Real containers, a real browser, real SQLite; binary deliverables are opened by independent readers.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_TMP = tempfile.mkdtemp(prefix="m03_")
os.environ.update(DB_PATH=str(Path(_TMP) / "veri" / "platform.db"), WORKSPACES_DIR=str(Path(_TMP) / "veri" / "workspaces"), PREVIEW_PORT="8061")
sys.path.insert(0, str(ROOT / "master"))

import atomic_io  # noqa: E402
import done_gate  # noqa: E402
import workspace_builder as wb  # noqa: E402
import workspace_docker  # noqa: E402

PROOF = ROOT / "eval" / "reports" / "milestone_03.json"
APP = '''import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()


def db():
    conn = sqlite3.connect("notlar.db")
    conn.execute("CREATE TABLE IF NOT EXISTS notlar (id INTEGER PRIMARY KEY, metin TEXT, bitti INTEGER DEFAULT 0)")
    return conn


class Not(BaseModel):
    metin: str


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/notlar")
def liste():
    with db() as c:
        return [{"id": i, "metin": m, "bitti": bool(b)} for i, m, b in c.execute("SELECT id, metin, bitti FROM notlar")]


@app.post("/api/notlar", status_code=201)
def ekle(n: Not):
    if not n.metin.strip():
        raise HTTPException(422, "boş")
    with db() as c:
        c.execute("INSERT INTO notlar (metin) VALUES (?)", (n.metin,))
    return {"ok": True}


@app.put("/api/notlar/{i}/bitti")
def isaretle(i: int):
    with db() as c:
        c.execute("UPDATE notlar SET bitti = 1 - bitti WHERE id=?", (i,))
    return {"ok": True}


@app.delete("/api/notlar/{i}")
def sil(i: int):
    with db() as c:
        c.execute("DELETE FROM notlar WHERE id=?", (i,))
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def sayfa():
    return PAGE


PAGE = """<!doctype html><meta charset="utf-8"><title>Notlar</title><link rel="icon" href="data:,"><h1>Notlar</h1>
<form id="f"><input id="m" aria-label="Not"><button type="submit">Ekle</button></form><p id="h"></p><input type="search" id="a" placeholder="Ara" aria-label="Ara"><ul id="l"></ul>
<script>
async function yukle(){ const r = await fetch('/api/notlar'); const veri = await r.json(); l.replaceChildren(...veri.filter(n => n.metin.toLocaleLowerCase('tr').includes(a.value.toLocaleLowerCase('tr'))).map(n => { const li = document.createElement('li'); li.textContent = n.metin + ' '; const k = document.createElement('input'); k.type = 'checkbox'; k.checked = n.bitti; k.setAttribute('aria-label', 'Bitti'); k.onchange = () => fetch('/api/notlar/' + n.id + '/bitti', {method: 'PUT'}); li.append(k); const b = document.createElement('button'); b.textContent = 'Sil'; b.onclick = async () => { await fetch('/api/notlar/' + n.id, {method: 'DELETE'}); yukle(); }; li.append(b); return li; })); }
f.addEventListener('submit', async e => { e.preventDefault(); const r = await fetch('/api/notlar', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({metin: m.value})}); h.textContent = r.ok ? '' : 'Boş not eklenemez'; if (r.ok) m.value = ''; yukle(); });
a.addEventListener('input', yukle);
yukle();
</script>"""
'''
MEMORY_ONLY = APP.replace('sqlite3.connect("notlar.db")', 'sqlite3.connect("file::memory:?cache=shared", uri=True)').replace(
    "def db():\n", "KEEP = sqlite3.connect('file::memory:?cache=shared', uri=True, check_same_thread=False)\n\n\ndef db():\n")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def project(name: str, source: str) -> Path:
    ws = wb.safe_workspace_dir(name)
    atomic_io.write_text(ws / "app.py", source)
    atomic_io.write_text(ws / "requirements.txt", "fastapi\nuvicorn\n")
    return ws


def real_application() -> str:
    ws = project("notlar", APP)
    status, detail = done_gate.server_proof(ws)
    check(status == done_gate.PASSED, detail)
    for step in ("kayıt isteği 201 döndü", "veritabanında satır arttı", "sayfa yenilenince duruyor", "sunucu yeniden başlayınca duruyor", "boş gönderim", "silme kalıcı", "durum değişikliği kalıcı", "arama süzüyor", "API denetimi"):
        check(step in detail, f"adım eksik: {step}: {detail}")
    shots = sorted(p.name for p in (ws / ".ai-os" / "filmstrip").glob("*.png"))
    check(len(shots) >= 6 and not (ws / "notlar.db").exists(), f"film şeridi {shots} ya da projeye veri yazıldı")
    evidence = json.loads((ws / done_gate.EVIDENCE).read_text(encoding="utf-8"))
    check(evidence["requests"] and evidence["rows"]["gönderim-sonrası"] and evidence["screenshots"] == shots, "kanıt dosyası eksik")
    check(any("rastgele ekleme/silme" in c for c in evidence["api"]["checked"]), f"özellik testi koşmadı: {evidence['api']}")
    record = done_gate._record(ws, done_gate.Delivery({s: (done_gate.PASSED, "") for s in "ABC"}))
    proof = json.loads((ws / done_gate.RECORD).read_text(encoding="utf-8"))
    check(record[0] == done_gate.PASSED and proof["evidence"] and proof["generation"]["model"] and len(proof["generation"]["digest"]) > 20, str(proof.get("generation")))
    check("sayfa, API ile aynı kayıtları gösteriyor" in evidence["api"]["checked"], f"sayfa karşılaştırılmadı: {evidence['api']}")
    return f"{len(evidence['steps'])} yolculuk adımı ve {len(evidence['api']['checked'])} API kontrolü geçti, {len(evidence['requests'])} HTTP izi, {len(shots)} ekran görüntüsü"


def memory_only_application() -> str:
    status, detail = done_gate.server_proof(project("bellek", MEMORY_ONLY))
    check(status == done_gate.FAILED and "sunucu yeniden başlayınca" in detail, f"yalnız bellekte tutan uygulama yakalanmadı: {detail}")
    return f"yalnız bellekte tutan sahte kalıcılık yakalandı: {detail[:90]}"


def crashing_application() -> str:
    status, detail = done_gate.server_proof(project("cokuk", "from fastapi import FastAPI\napp = FastAPI()\nraise RuntimeError('açılışta çöker')\n"))
    check(status == done_gate.FAILED and "açılışta çöker" in detail, detail)
    return "açılışta çöken sunucu, kendi hata satırıyla raporlandı"


def artifacts() -> str:
    import openpyxl
    from PIL import Image

    import artifact_check

    folder = Path(_TMP) / "dosyalar"
    folder.mkdir()
    book = openpyxl.Workbook()
    book.active.append(["a", "b"])
    book.active.append([1, "=A2*2"])
    book.save(folder / "iyi.xlsx")
    book.active["B2"] = "=A2/0"
    book.save(folder / "hatali.xlsx")
    Image.new("RGB", (40, 30), "white").save(folder / "bos.png")
    (folder / "bozuk.pdf").write_bytes(b"%PDF-1.7\nbozuk")
    results = {name: artifact_check.problems(folder / name) for name in ("iyi.xlsx", "hatali.xlsx", "bos.png", "bozuk.pdf")}
    check(results["iyi.xlsx"] == [] and results["hatali.xlsx"] and results["bos.png"] and results["bozuk.pdf"], str(results))
    return f"bağımsız okuyucular: hatalı Excel, boş görsel ve bozuk PDF reddedildi: {results['hatali.xlsx'][0][:60]}"


def wrong_status_and_lying_api() -> str:
    status, detail = done_gate.server_proof(project("durum200", APP.replace(", status_code=201", "")))
    check(status == done_gate.FAILED and "201" in detail, f"200 dönen oluşturma yakalanmadı: {detail}")
    lying = APP.replace('c.execute("DELETE FROM notlar WHERE id=?", (i,))', 'c.execute("DELETE FROM notlar WHERE id=?", (i + 100000,))')
    status, detail = done_gate.server_proof(project("yalanci", lying))
    check(status == done_gate.FAILED and ("silme" in detail or "uyuşmuyor" in detail), f"silmeyen API yakalanmadı: {detail}")
    return f"201 dönmeyen ve 'sildim' deyip silmeyen uygulamalar reddedildi: {detail[:80]}"


TESTS = (("gerçek uygulama yenileme ve yeniden başlatmadan sağ çıkar", real_application), ("sahte kalıcılık yakalanır", memory_only_application),
         ("çöken sunucu raporlanır", crashing_application), ("yanlış durum kodu ve yalancı API yakalanır", wrong_status_and_lying_api), ("ikili dosyalar bağımsız okuyucuyla açılır", artifacts))


def main() -> int:
    check(workspace_docker.available(), "Docker kapalı: kanıt alınamaz")
    results = {}
    for name, test in TESTS:
        try:
            detail, ok = test(), True
        except Exception as exc:
            detail, ok = f"{type(exc).__name__}: {exc}"[:600], False
        results[name] = {"ok": ok, "detail": detail}
        print(f"{'GEÇTİ' if ok else 'KALDI'} {name}: {detail}", flush=True)
    PROOF.parent.mkdir(parents=True, exist_ok=True)
    PROOF.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    atomic_io.remove_tree(_TMP)
    return 0 if all(r["ok"] for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
