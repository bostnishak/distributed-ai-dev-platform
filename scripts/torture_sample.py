"""The sample application of the milestone 06 proof: a correct expense list and copies with one bug injected each."""

from __future__ import annotations

_APP = '''import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()


def db():
    conn = sqlite3.connect("kalemler.db", timeout=20)
    conn.execute("CREATE TABLE IF NOT EXISTS kalemler (id INTEGER PRIMARY KEY, metin TEXT, kurus INTEGER, tutar REAL)")
    return conn


class Kalem(BaseModel):
    metin: str
    tutar: float = 0


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/kalemler")
def liste():
    with db() as c:
        return [{"id": i, "metin": m, "kurus": k, "tutar": t} for i, m, k, t in c.execute("SELECT id, metin, kurus, tutar FROM kalemler ORDER BY id")]


@app.post("/api/kalemler", status_code=201)
def ekle(k: Kalem):
    if not k.metin.strip():
        raise HTTPException(422, "boş")
    with db() as c:
        c.execute("INSERT INTO kalemler (metin, kurus, tutar) VALUES (?,?,?)", (k.metin, round(k.tutar * 100), k.tutar))
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def sayfa():
    return PAGE


PAGE = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Harcama</title><link rel="icon" href="data:,">
<h1>Harcama defteri</h1><input id="m" aria-label="Açıklama"><input id="t" type="number" step="0.01" aria-label="Tutar"><button id="e">Ekle</button>
<input id="a" type="search" aria-label="Ara"><p id="h" role="alert"></p><p id="s"></p><ul id="l"></ul>
<script>
const $ = id => document.getElementById(id); let items = [];
const fold = x => x.toLocaleLowerCase('tr');
function render() {
  $('l').replaceChildren(...items.filter(x => fold(x.metin).includes(fold($('a').value))).map(x => { const li = document.createElement('li'); li.textContent = x.metin + ' — ' + (x.kurus / 100).toFixed(2); return li; }));
  $('s').textContent = 'Toplam: ' + (items.reduce((sum, x) => sum + x.kurus, 0) / 100).toFixed(2);
}
async function load() { try { items = await (await fetch('/api/kalemler')).json(); render(); } catch { $('h').textContent = 'Liste yüklenemedi: bağlantı hatası'; } }
$('e').addEventListener('click', async () => {
  const metin = $('m').value.trim(); if (!metin) return;
  $('e').disabled = true; $('h').textContent = 'Kaydediliyor';
  try {
    const r = await fetch('/api/kalemler', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({metin, tutar: Number($('t').value || 0)})});
    if (!r.ok) throw new Error(r.status);
    $('m').value = ''; $('t').value = ''; $('h').textContent = ''; await load();
  } catch { $('h').textContent = 'Kayıt eklenemedi: sunucu hatası, tekrar dene'; }
  finally { $('e').disabled = false; }
});
$('a').addEventListener('input', render); load();
</script>"""
'''

BUGS = {"0.1+0.2 para hatası": "para hesabı", "çift gönderim": "çift gönderim", "Türkçe İ/ı arama": "Türkçe arama", "sessiz kayıt hatası": "sunucu hatası"}

_EDITS = {
    "0.1+0.2 para hatası": (("(items.reduce((sum, x) => sum + x.kurus, 0) / 100).toFixed(2)", "items.reduce((sum, x) => sum + x.tutar, 0)"),),
    "çift gönderim": (("$('e').disabled = true; ", ""), ("const metin = $('m').value.trim(); if (!metin) return;", "const metin = $('m').value.trim(); if (!metin) return; await new Promise(done => setTimeout(done, 200));")),
    "Türkçe İ/ı arama": (("const fold = x => x.toLocaleLowerCase('tr');", "const fold = x => x.toLowerCase();"),),
    "sessiz kayıt hatası": (("catch { $('h').textContent = 'Kayıt eklenemedi: sunucu hatası, tekrar dene'; }", "catch { $('m').value = ''; $('h').textContent = ''; }"),),
}


def app_source(bug: str) -> str:
    source = _APP
    for old, new in _EDITS.get(bug, ()):
        assert old in source, f"enjeksiyon yeri bulunamadı: {old}"
        source = source.replace(old, new)
    return source
