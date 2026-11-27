"""Live checks for the specification items that so far only had unit tests.

Usage: python scripts/live_items.py [group ...]     groups: direct, server
Real local models, real Docker sandbox, real browser, real server on port 8031 with its own temporary data folder.
Every check is decided by code and printed with the item it covers; exit 0 only when all pass.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "master"
_TMP = Path(tempfile.mkdtemp(prefix="items_"))
os.environ.update(DB_PATH=str(_TMP / "veri" / "platform.db"), WORKSPACES_DIR=str(_TMP / "veri" / "workspaces"), PREVIEW_PORT="8059", PYTHONUTF8="1", DOCKER_CLI_HINTS="false")
sys.path[:0] = [str(MASTER), str(ROOT / "scripts")]

import golden  # noqa: E402

import atomic_io  # noqa: E402
import workspace_builder as wb  # noqa: E402

PORT = 8031
golden.BASE = f"http://127.0.0.1:{PORT}"
REPORT = ROOT / "eval" / "reports" / "live_items.json"
CHECKS: list[tuple[str, str, object]] = []


def item(group: str, name: str):
    def register(function):
        CHECKS.append((group, name, function))
        return function

    return register


def need(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(str(message)[:500])


def project(name: str, files: dict[str, str]) -> Path:
    ws = wb.safe_workspace_dir(name)
    for relative, content in files.items():
        atomic_io.write_text(ws / relative, content)
    return ws


def run(coroutine):
    return asyncio.run(coroutine)


# --- direct: real model, sandbox and browser ------------------------------------------------------------------------

@item("direct", "v1 IntakeAgent şemalı spec")
def intake():
    import agent_contracts

    spec = run(agent_contracts.intake("Bir kütüphane için kitap ekleme ve silme butonları olan web uygulaması. Ana renk #224466."))
    dumped = spec.model_dump_json()
    need("#224466" in dumped.lower() or "224466" in dumped, dumped)
    return f"şemalı spec üretildi ({len(dumped)} karakter, renk korunmuş)"


@item("direct", "v1 ArchitectAgent plan ve risk denetimi")
def architect():
    import agent_contracts

    review = run(agent_contracts.review("Kullanıcı parolalarını düz metin olarak saklayan ve herkese açık bir giriş sistemi yap."))
    dumped = review.model_dump_json().casefold()
    need(any(w in dumped for w in ("parola", "şifre", "hash", "güvenlik", "password")), dumped)
    return "güvensiz istek için risk uyarısı verdi"


@item("direct", "v2 AST çapalı nokta atışı yama")
def patch():
    import patch_edit

    current = "<h1>Liste</h1>\n<button id='ekle'>Ekle</button>\n<footer>Sürüm 1</footer>\n" * 1 + "\n".join(f"<p>satır {i}</p>" for i in range(200))

    async def generate(system: str, user: str) -> str:
        return await wb._ollama_generate(await wb.pick_coder_model(None), system, user, num_predict=800, temperature=0.1)

    ask = f"Değişiklik isteği: 'Ekle' düğmesinin yazısını 'Kaydet' yap.\nHedef dosya: `index.html`\n\nMevcut dosya içeriği:\n```\n{current}\n```\n\nBu dosyanın güncel ve EKSİKSİZ tüm içeriğini yaz."  # as the product builds it
    patched = run(patch_edit.try_patch(generate, ask, current))
    need(patched is not None and "Kaydet" in patched and patched.count("<p>satır") == 200 and "Sürüm 1" in patched, patched[:300] if patched else "yama uygulanmadı")
    return "yalnız istenen yer değişti, 200 satır korundu"


@item("direct", "v1 HTML/JS/Python/JSON sözdizimi denetimi")
def syntax():
    import workspace_checks

    ws = project("sozdizimi", {"app.js": "function a( {", "x.py": "def f(:\n", "d.json": "{,}", "index.html": "<script src='app.js'></script>"})
    found = workspace_checks.js_syntax_problem(ws)
    need(found is not None and found[0].name == "app.js", found)
    need(len(wb.verify_workspace_files(ws)) >= 2, wb.verify_workspace_files(ws))
    return "JS, Python ve JSON hataları dosyasıyla bulundu"


@item("direct", "v1 Spec uyum denetçisi (gerçek sayfa)")
def spec_check():
    import spec_contract

    request = 'Başlık "Depo Takip" olsun, "Stok Ekle" butonu ve #aa3300 rengi olsun.'
    ws = project("uyum", {"index.html": "<h1>Depo</h1><button>Ekle</button>"})
    need(spec_contract.problem(ws, request) is not None, "eksik sayfa kabul edildi")
    atomic_io.write_text(ws / "index.html", "<style>h1{color:#aa3300}</style><h1>Depo Takip</h1><button>Stok Ekle</button>")
    need(spec_contract.problem(ws, request) is None, spec_contract.problem(ws, request))
    return "eksik etiket ve renk reddedildi, tam sayfa kabul edildi"


@item("direct", "v1 Yer tutucu tarayıcı (çalıştırma kapısı)")
def placeholder():
    import workspace_smoke

    ws = project("yer", {"index.html": "<!doctype html><meta charset='utf-8'><h1>Panel</h1><p>Lorem ipsum dolor sit amet</p><button onclick='x()'>Ekle</button><script>function x(){/* TODO: implement */}</script>"})

    async def go():
        async def regenerate(_path, _ask):
            return ""

        return [e async for e in workspace_smoke.smoke_and_repair(ws, regenerate, rounds=0)]

    final = run(go())[-1]
    need(not final["ok"] and final["warning"], final)
    return final["warning"][:150]


@item("direct", "v2 Karmaşıklığa göre model basamağı ve @fast/@deep")
def gears():
    import complexity_governor

    simple, hard = complexity_governor.classify("Ankara'nın nüfusu kaç?"), complexity_governor.classify("Çok kiracılı, ödeme entegrasyonlu, mikroservis mimarili bir ERP tasarla ve güvenliğini doğrula")
    forced_fast, forced_deep = complexity_governor.classify("@fast bir ERP tasarla"), complexity_governor.classify("@deep merhaba")
    need(simple.level < hard.level and forced_fast.level < forced_deep.level, (simple, hard, forced_fast, forced_deep))
    return f"basit={simple.level}, ağır={hard.level}, @fast={forced_fast.level}, @deep={forced_deep.level}"


@item("direct", "v3 Şemaya zorlanmış JSON ve role göre sıcaklık")
def schema():
    import gateway

    shape = {"type": "object", "properties": {"sehir": {"type": "string"}, "nufus_milyon": {"type": "number"}}, "required": ["sehir", "nufus_milyon"]}

    async def go():
        return await gateway.default_client.chat([{"role": "user", "content": "Türkiye'nin başkenti ve yaklaşık nüfusu"}], model="qwen3.5:4b", profile="extract", format_schema=shape, num_predict=200, feature="live_items")

    data = json.loads(run(go()).content)
    need(set(shape["required"]) <= set(data) and "ankara" in data["sehir"].casefold(), data)
    return f"şemaya uyan JSON: {data}"


@item("direct", "v1 Kurulu modelleri keşfetme, role göre seçim, yedek")
def models():
    from gateway import registry

    chosen = run(wb.pick_coder_model(None))
    missing = run(wb.pick_coder_model("olmayan-model:99b"))
    need(chosen and missing and missing != "olmayan-model:99b", (chosen, missing))
    registry.init_registry_db()
    return f"seçilen {chosen}; olmayan model yerine {missing}"


@item("direct", "v2 keep_alive / num_ctx boyutlama")
def context_size():
    import gateway

    async def go():
        await gateway.default_client.chat([{"role": "user", "content": "tamam yaz"}], model="qwen3.5:4b", num_predict=5, num_ctx=2048, feature="live_items")

    run(go())
    loaded = httpx.get("http://127.0.0.1:11434/api/ps", timeout=10).json()["models"]
    entry = next((m for m in loaded if m["name"].startswith("qwen3.5:4b")), None)
    need(entry is not None and entry.get("context_length", 2048) <= 4096 and entry.get("expires_at"), loaded)
    return f"bellekte context={entry.get('context_length')}, süre sonu ayarlı"


@item("direct", "v2 Etki alanı ve yalnız etkilenen testler")
def blast():
    import repo_map

    ws = project("etki", {"para.py": "def kdv(x):\n    return x * 1.2\n", "fatura.py": "from para import kdv\n\ndef toplam(a):\n    return kdv(sum(a))\n",
                          "depo.py": "def say(a):\n    return len(a)\n", "tests/test_fatura.py": "from fatura import toplam\n\ndef test_t():\n    assert toplam([10]) == 12\n",
                          "tests/test_depo.py": "from depo import say\n\ndef test_s():\n    assert say([1]) == 1\n"})
    tests = repo_map.affected_tests(ws, ["para.py"])
    note = repo_map.dependents_note(ws, ["para.py"])
    need(any("test_fatura" in t for t in tests) and not any("test_depo" in t for t in tests) and "fatura.py" in note, (tests, note))
    return f"yalnız {tests} seçildi; not: {note[:90]}"


@item("direct", "v2 Yalıtılmış çalıştırma: ağsız kutu")
def sandbox_isolation():
    from sandbox import runner

    ws = project("yalitim", {"x.py": "import socket\ntry:\n    socket.create_connection(('1.1.1.1', 80), 3)\n    print('AG ACIK')\nexcept OSError as e:\n    print('AG KAPALI', type(e).__name__)\n"})
    result = runner.run_workspace_command(ws, ["python", "/sandbox/x.py"], timeout_s=40)
    need("AG KAPALI" in result["stdout"], result)
    return "kutudan ağa çıkılamadı"


@item("direct", "v3 WASM ve iş nesnesi yalıtımı")
def wasm_job():
    import isolation

    done = isolation.run_capped([sys.executable, "-c", "x = bytearray(900_000_000); print(len(x))"], memory_mb=200, timeout_s=30)
    need(done.returncode != 0, done)
    wat = '(module (func (export "kare") (param i32) (result i32) local.get 0 local.get 0 i32.mul))'
    need(isolation.run_wasm(wat, "kare", 12) == 144, "wasm yanlış sonuç")
    return "200 MB sınırında 900 MB ayıran süreç durduruldu; WASM sonucu doğru"


@item("direct", "v3 Yerleşim geometrisi ve kontrast denetimi")
def layout():
    import visual_audit

    ws = project("gorsel", {"index.html": "<meta charset='utf-8'><body style='margin:0'><p style='color:#bbb;background:#fff'>zor okunan metin</p><div style='width:1600px'>taşan içerik</div>"})
    found = visual_audit.audit(ws)
    need(found and any("kontrast" in f for f in found), found)
    return "; ".join(found[:2])[:200]


@item("direct", "v3 Akış analizi ve N+1 / SQL planı")
def analysis():
    import code_audit

    flows = code_audit.flows("from fastapi import FastAPI\nimport os\napp = FastAPI()\n@app.get('/x')\ndef x(ad: str):\n    os.system('echo ' + ad)\n")
    loops = code_audit.loops_with_queries("def f(db, ids):\n    for i in ids:\n        db.execute('SELECT * FROM t WHERE id=?', (i,))\n")
    ws = project("plan", {"schema.sql": "CREATE TABLE t (id INTEGER PRIMARY KEY, ad TEXT);", "q.py": "SQL = 'SELECT * FROM t WHERE ad = ?'\n"})
    scans = code_audit.full_scans(ws)
    need(flows and loops and scans, (flows, loops, scans))
    return f"komut akışı {flows[0][1][:50]!r}, döngüde sorgu satır {loops[0]}, tam tarama: {scans[0][:60]}"


@item("direct", "v3 Lisans uyum kapısı (gerçek paket kaydı)")
def licences():
    import code_audit

    ws = project("lisans", {"requirements.txt": "mysqlclient\n", "LICENSE": "MIT License\n\nPermission is hereby granted, free of charge", "a.py": "x=1\n"})
    found = code_audit.licence_conflicts(ws, "MIT lisanslı proje", code_audit.registry_licence)
    need(found and "mysqlclient" in found[0], found)
    return found[0][:150]


@item("direct", "v4 Sürüme bağlı belge kasası ve çevrimdışı mod")
def docs():
    import docs_vault

    online = docs_vault.brief("fastapi ile bir API yaz")
    need("fastapi" in online.casefold() and any(ch.isdigit() for ch in online), online)
    offline = docs_vault.brief("fastapi ile bir API yaz", fetch=lambda *_a: None)
    need(offline and "fastapi" in offline.casefold(), "çevrimdışıyken kasa boş döndü")
    return online.splitlines()[-1][:150]


@item("direct", "v4 Tasarım kuralları, şablon dedektörü, OKLCH palet")
def design():
    import design_slop
    import design_system

    colours = design_system.palette("sakin bir yoga stüdyosu", dark=False)
    values = list(colours.values())
    need(len(values) >= 3 and max(design_system.contrast(values[0], v) for v in values[1:]) >= 4.5, colours)
    ws = project("slop", {"index.html": "<style>body{background:linear-gradient(135deg,#667eea,#764ba2);font-family:Inter}</style><h1>🚀 Welcome to Our Amazing Platform</h1><div>✨ Feature 1</div>"})
    need(design_slop.findings(ws, "yoga stüdyosu"), "şablon görünüm fark edilmedi")
    return f"palet {list(colours)[:3]}; şablon uyarısı: {design_slop.findings(ws, 'yoga')[0][:70]}"


@item("direct", "v3 Parametrik benchmark ve istatistiksel sürüm kapısı")
def statistics_gate():
    import eval_stats

    ok_gate, line = eval_stats.gate([False] * 12 + [True] * 8, [True] * 20)  # significantly better: promoted
    bad_gate, _ = eval_stats.gate([True] * 20, [False] * 12 + [True] * 8)
    need(ok_gate and not bad_gate and eval_stats.sprt([True] * 40) != eval_stats.sprt([False] * 40), (ok_gate, bad_gate, line))
    return "gerileyen sonuç kapıdan geçmedi"


@item("direct", "v3 Otomatik geri alma")
def rollback():
    import release_guard

    release_guard.PROMPTS = _TMP / "istemler"
    release_guard.PROMPTS.mkdir(exist_ok=True)
    (release_guard.PROMPTS / "a.txt").write_text("iyi istem", encoding="utf-8")
    release_guard.promote({"s1": True, "s2": True})
    (release_guard.PROMPTS / "a.txt").write_text("bozuk istem", encoding="utf-8")
    verdict = release_guard.compare({"s1": True, "s2": False})
    need(verdict[0] == "regressed", verdict)
    release_guard.rollback()
    need((release_guard.PROMPTS / "a.txt").read_text(encoding="utf-8") == "iyi istem", "istem geri alınmadı")
    return "gerileyen koşuda istem eski haline döndü"


@item("direct", "v4 Dockersız yerel mod ve ai-os doctor/bench girişi")
def local_mode():
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "ai_os.py"), "doctor"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, check=False)
    need(done.returncode == 0 and "docker" in done.stdout.casefold(), done.stdout[-400:] + done.stderr[-200:])
    return "doctor çalıştı, Docker durumunu bildiriyor"


# --- server: through the HTTP surface of a real server --------------------------------------------------------------

@item("server", "v1 Yalıtılmış çalışma alanı: yol kaçışı koruması")
def traversal():
    ws = project("kacis", {"index.html": "x"})
    for attempt in ("../../platform.db", "..%2F..%2Fplatform.db", "C:/Windows/win.ini"):
        response = httpx.get(f"{golden.BASE}/api/studio/workspaces/{ws.name}/file", params={"path": attempt}, timeout=30)
        need(response.status_code >= 400 or ("SQLite" not in response.text and "[fonts]" not in response.text), (attempt, response.status_code, response.text[:80]))
    return "üç kaçış denemesi de reddedildi"


@item("server", "v1 Proje durumu ve sürüm anlık görüntüsü + v3 zaman yolculuğu")
def versions():
    ws = project("surum", {"index.html": "<h1>v1</h1>"})
    wb.create_snapshot(ws, "ilk")
    saved = httpx.put(f"{golden.BASE}/api/studio/workspaces/{ws.name}/file", json={"path": "index.html", "content": "<h1>v2</h1>"}, timeout=30)
    need(saved.status_code == 200, saved.text)
    history = httpx.get(f"{golden.BASE}/api/studio/workspaces/{ws.name}/history", timeout=30).json()
    back = httpx.post(f"{golden.BASE}/api/studio/workspaces/{ws.name}/restore/v1", timeout=30)
    need(back.status_code == 200 and "v1" in (ws / "index.html").read_text(encoding="utf-8"), (history, back.text))
    return "düzenlendi, v1'e dönüldü"


@item("server", "v1 Uzun süreli tercih belleği")
def preference():
    golden.chat("Bundan sonra her zaman yanıtlarının sonuna 'Kolay gelsin' yaz.")
    reply = golden.chat("Stok sayımı nasıl yapılır, iki cümleyle anlat.")
    need("kolay gelsin" in reply.text.casefold(), reply.text[-200:])
    listed = golden.chat("tercihlerimi göster")
    golden.chat("tercihlerimi sil")
    need("Kolay gelsin" in listed.text, listed.text)
    return "yeni sohbette tercih uygulandı, listelendi, silindi"


@item("server", "v3 İki zamanlı bellek, birleştirme, denetim ve silme")
def memory():
    for text in ("Şirketimizin veritabanı SQLite.", "Şirketimizin veritabanı artık PostgreSQL."):
        golden.chat(text)
    facts = httpx.get(f"{golden.BASE}/api/memory/facts", params={"user_id": "golden"}, timeout=30).json()
    consolidated = httpx.post(f"{golden.BASE}/api/memory/consolidate", params={"user_id": "golden"}, timeout=60)
    view = httpx.get(f"{golden.BASE}/api/studio/memory-view", timeout=30)
    need(view.status_code == 200 and consolidated.status_code in (200, 422), (facts, consolidated.text[:200]))
    items = facts.get("facts", facts) if isinstance(facts, dict) else facts
    need(items, f"hiç bilgi öğrenilmedi: {facts}")
    removed = httpx.delete(f"{golden.BASE}/api/memory/facts/{items[0]['id']}", params={"user_id": "golden"}, timeout=30)
    need(removed.status_code == 200, removed.text)
    return f"{len(items)} bilgi öğrenildi, birleştirme uç noktası {consolidated.status_code}, silme çalıştı"


@item("server", "v2 Sır tarayıcı ve SAST (projede)")
def sast():
    ws = project("sir", {"app.py": "API_KEY = 'sk-proj-" + "A1b2" * 10 + "'\nimport os\ndef f(x):\n    os.system('rm ' + x)\n"})
    result = httpx.get(f"{golden.BASE}/api/studio/workspaces/{ws.name}/security-scan", timeout=60).json()
    result = result.get("security", result)
    need(result.get("total_issues", 0) >= 2 and not result.get("ok"), result)
    return f"{result['total_issues']} bulgu"


@item("server", "v2 Yörünge toplama ve sır temizleme")
def trajectory():
    secret = "sk-proj-" + "Zz91" * 10
    golden.chat(f"Tek HTML dosyası olarak boş bir merhaba sayfası yap. (anahtarım {secret})")
    summary = httpx.get(f"{golden.BASE}/api/studio/runs/summary", timeout=30).json()
    stored = "".join(p.read_text(encoding="utf-8", errors="ignore") for p in (_TMP / "veri").rglob("*.json*") if p.is_file())
    need(json.dumps(summary) != "{}" and secret not in stored and secret not in json.dumps(summary), "gizli anahtar kayda geçti" if secret in stored else summary)
    return "üretim kaydedildi, anahtar kayıtta yok"


@item("server", "v2 Doğrulanmış beceri kütüphanesi + v2 defter (doğrulandı/varsayım)")
def skills():
    spaces = httpx.get(f"{golden.BASE}/api/studio/workspaces", timeout=30).json()
    listed = spaces.get("workspaces", spaces) if isinstance(spaces, dict) else spaces
    built = next((w for w in listed if "merhaba" in str(w.get("name", "")).casefold() or "merhaba" in str(w.get("prompt", "")).casefold()), None)
    need(built is not None, "üretilen proje listede yok")
    proof = httpx.get(f"{golden.BASE}/api/studio/workspaces/{built['id']}/proof", timeout=30).json()
    skill_file = _TMP / "veri" / "skills.json"
    need(proof.get("ledger", {}).get("verified") is not None and proof.get("signed"), proof)
    need(skill_file.is_file() and json.loads(skill_file.read_text(encoding="utf-8")), "doğrulanmış üretim beceri kartı olmadı")
    return f"defterde {len(proof['ledger'].get('verified', []))} doğrulanmış madde; beceri kartı yazıldı"


@item("server", "v2 L1/L2 önbellek (aynı belge sorusu)")
def caches():
    text = "\n".join(f"Madde {i}: bakım adımı anlatılır." for i in range(700)) + "\nYıllık sigorta primi 73250 TL olarak ödenir.\n"
    file = ("sozlesme.txt", text.encode(), "text/plain")
    started = time.time()
    first = golden.chat("Belgenin tamamına bak: sigorta primi ne kadar?", file=file)
    slow = time.time() - started
    started = time.time()
    second = golden.chat("Belgenin tamamına bak: sigorta primi ne kadardır?", file=file)
    fast = time.time() - started
    need("73250" in golden.digits(first.text) and "73250" in golden.digits(second.text) and fast < slow / 3 and "değişmediği" in second.text, (slow, fast, second.text[-200:]))
    return f"ilk {slow:.0f} sn, benzer soru {fast:.1f} sn (önbellekten, bunu söylüyor)"


@item("server", "v2 MCP veri yolu: yazan araç onaysız çalışmaz")
def mcp():
    listed = httpx.post(f"{golden.BASE}/api/mcp-server/rpc", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, timeout=30)
    need(listed.status_code == 200 and listed.json().get("result", {}).get("tools"), listed.text[:300])
    created = httpx.post(f"{golden.BASE}/api/mcp/connectors", json={"name": "deneme", "url": "http://169.254.169.254/latest", "transport": "http"}, timeout=30)
    need(created.status_code >= 400, f"iç ağ adresine bağlayıcı kabul edildi: {created.status_code} {created.text[:200]}")
    return f"{len(listed.json()['result']['tools'])} araç listelendi; iç ağ adresi reddedildi"


@item("server", "v2 Eylem yetki kapısı ve v3 leke/politika")
def gate_policy():
    import policy

    refused = policy.check("browser_submit", integrity=policy.UNTRUSTED)
    allowed = policy.check("browser_submit", integrity=policy.UNTRUSTED, approved=True)
    secret = policy.check("mcp_call", integrity=policy.UNTRUSTED, payload="sk-proj-" + "A1b2" * 10, approved=True)
    need(not refused.allowed and allowed.allowed and not secret.allowed, (refused, allowed, secret))
    return "güvenilmeyen içerik onaysız yazamıyor; sır dışarı çıkamıyor"


@item("server", "v2 İki varyant yan yana")
def variants():
    reply = golden.chat("iki varyant: kitap listesi gösteren tek sayfalık web uygulaması tasarla")
    need(reply.text.count("Varyant") >= 2 and "2 varyant hazır" in reply.text and reply.workspace, reply.text[-300:])
    return "iki ayrı proje kartı üretildi"


@item("server", "v4 Sertleştirilmiş Dockerfile/Compose ve gerçek derleme")
def deploy():
    reply = golden.chat("FastAPI ile /health ve /api/sayi uçları olan küçük bir API yap; Dockerfile ve docker-compose da ekle.")
    need(reply.workspace, reply.text[-300:])
    ws = wb.safe_workspace_dir(reply.workspace["workspace"]["id"])
    need((ws / "Dockerfile").is_file() and (ws / "docker-compose.yml").is_file(), [p.name for p in ws.iterdir()])
    dockerfile = (ws / "Dockerfile").read_text(encoding="utf-8")
    need("USER" in dockerfile and "root" not in dockerfile.split("USER")[-1][:20], dockerfile)
    tag = f"items-deploy-{int(time.time())}"
    built = subprocess.run([shutil.which("docker"), "build", "-q", "-t", tag, str(ws)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=500, check=False)
    subprocess.run([shutil.which("docker"), "rmi", "-f", tag], capture_output=True, timeout=60, check=False)
    need(built.returncode == 0, built.stderr[-400:])
    return "Dockerfile root olmayan kullanıcıyla; imaj gerçekten derlendi"


@item("server", "v4 Sunum, slayt denetimi ve uzun yazıda sayı tutarlılığı")
def documents():
    reply = golden.chat("Depo verimliliği üzerine 3 slaytlık sunum hazırla.")
    need("/api/assistant/media/" in reply.text and ("doğrulaması" in reply.text or "denetim" in reply.text.casefold()), reply.text[:400])
    return "sunum üretildi ve sayfa denetimi raporlandı"


@item("server", "v4 Zamanlanmış görevler")
def cron():
    import cronjobs

    job = cronjobs.add_job("deneme", "* * * * *", "144'ün karekökü kaç?")

    async def runner(prompt: str, *_args) -> str:
        return golden.chat(prompt).text

    ran = run(cronjobs.run_due(runner, now=datetime.now(UTC)))
    recent = cronjobs.recent_runs(job["id"] if isinstance(job, dict) else None)
    cronjobs.remove_job(job["id"])
    need(recent and "12" in json.dumps(recent, ensure_ascii=False), (ran, recent))
    return "zamanı gelen görev çalıştı ve sonucu kaydedildi"


@item("server", "v2 Öncelikli GPU kuyruğu (sohbet arka planın önüne geçer)")
def priority():
    from gateway import priority_gate

    async def go():
        gate, order = priority_gate.PriorityGate(1), []

        async def use(name, feature):
            async with gate.slot(feature):
                order.append(name)
                await asyncio.sleep(0.05)

        priority_gate._wait_until_safe = lambda: asyncio.sleep(0)
        first = asyncio.create_task(use("ilk", "chat"))
        await asyncio.sleep(0.01)
        rest = [asyncio.create_task(use("arka", "self_eval")), asyncio.create_task(use("sohbet", "chat"))]
        await asyncio.gather(first, *rest)
        return order

    order = run(go())
    need(order == ["ilk", "sohbet", "arka"], order)
    return "bekleyen arka plan işinden önce sohbet çalıştı"


@item("server", "v3 Çalışma anı bekçisi (duran proje sunucusu fark edilir)")
def watchdog_item():
    import event_log
    import process_utils
    import project_server
    import watchdog

    ws = project("bekci", {"main.py": "from fastapi import FastAPI\n\napp = FastAPI()\n\n\n@app.get('/health')\ndef health():\n    return {'ok': True}\n"})
    url = project_server.start(ws)
    need(httpx.get(url + "/health", timeout=10).json() == {"ok": True}, url)
    need(watchdog.check_servers() == [], "çalışan sunucu durmuş sayıldı")
    name = project_server._running[ws.name].server.name
    process_utils.run_process([shutil.which("docker"), "kill", name], timeout_s=60)
    dead = watchdog.check_servers()
    need(ws.name in dead and any("sunucu durdu" in e["kind"] for e in event_log.read(ws)), (dead, event_log.read(ws)))
    return f"gerçek sunucu {url} açıldı, yanıt verdi; kap öldürülünce bekçi kaydetti"


def start_server() -> subprocess.Popen:
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", PORT)) == 0:
            raise SystemExit(f"{PORT} portunda başka bir sunucu var; eski denemeyi kapat (yoksa eski kod sınanır)")
    server = subprocess.Popen([str(MASTER / "venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "app:app", "--app-dir", str(MASTER), "--host", "127.0.0.1", "--port", str(PORT)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            if httpx.get(golden.BASE + "/", timeout=2).status_code == 200:
                return server
        except httpx.HTTPError:
            time.sleep(0.5)
    server.kill()
    raise SystemExit("deneme sunucusu açılmadı")


def stop_server(server: subprocess.Popen) -> None:
    import psutil

    try:
        for process in [*psutil.Process(server.pid).children(recursive=True), psutil.Process(server.pid)]:
            process.kill()
    except psutil.NoSuchProcess:
        return


def main() -> int:
    import db

    db.init_db()
    wanted = set(sys.argv[1:]) or {"direct", "server"}
    only = os.environ.get("ITEM_FILTER", "")
    selected = [c for c in CHECKS if c[0] in wanted and only in c[1]]
    server = start_server() if any(c[0] == "server" for c in selected) else None
    results = {}
    try:
        for _group, name, function in selected:
            started = time.time()
            try:
                detail, ok = function(), True
            except Exception as exc:
                detail, ok = f"{type(exc).__name__}: {exc}"[:600], False
            results[name] = {"ok": ok, "detail": detail, "seconds": round(time.time() - started)}
            print(f"{'GEÇTİ' if ok else 'KALDI'} {name} ({results[name]['seconds']} sn): {detail}", flush=True)
    finally:
        if server:
            stop_server(server)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(_TMP, ignore_errors=True)
    passed = sum(r["ok"] for r in results.values())
    print(f"{passed}/{len(results)} geçti")
    return 0 if passed == len(results) else 1



if __name__ == "__main__":
    sys.exit(main())
