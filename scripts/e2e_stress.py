"""Live end-to-end stress test against a running server (real models, no stubs). Takes 10-25 minutes.

Usage: python scripts/e2e_stress.py [scenario ...]    (scenarios: web revision api flow pdf image)
Each scenario is verified programmatically; the exit code is the number of failures.
"""

import io
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "master"))
import spec_contract  # noqa: E402
import workspace_web  # noqa: E402

BASE = "http://127.0.0.1:8000"
WORKSPACES = ROOT / "master" / "data" / "workspaces"
WEB = (
    'Tek bir HTML dosyası olarak "Not Defteri" adlı bir web uygulaması yap. Harici kütüphane kullanma. '
    "Renkler: arka plan #101820, kartlar #1F2A36, ana buton #F2AA4C, metin #F5F5F5. Üst bar 56px yüksekliğinde. "
    'Bir metin alanı ve "Not Ekle" butonu olsun; eklenen notlar listede görünsün, her notta "Sil" butonu olsun. '
    'Üstte "Toplam not: 0" sayacı olsun ve her işlemde güncellensin. "Hepsini Sil" butonu listeyi boşaltsın. Örnek veri olmasın.'
)
CHANGE = "Ana buton rengini yeşil #10B981 yap."
API = (
    "FastAPI ve SQLite kullanan bir not API projesi yap: POST /notes (title zorunlu, 201 döner) ve GET /notes. "
    "requirements.txt ve README olsun."
)
FLOW = "Şu süreç için akış şeması çiz: Sipariş alınır, stok kontrol edilir, stok yoksa tedarik edilir, varsa paketlenir, kargoya verilir."
PDF = "Küçük bir kafede enerji tasarrufu için 2 sayfalık, tablolu bir PDF rapor hazırla."
IMAGE = '"Mavi Dalga" adlı bir kahve dükkanı için logo çiz.'


def chat(prompt, history=None):
    data = {"prompt": prompt, "history": json.dumps(history or [], ensure_ascii=False), "user_id": "e2e", "conversation_id": ""}
    text, box, errors = [], None, []
    with httpx.stream("POST", f"{BASE}/api/assistant/chat/stream", files={k: (None, v) for k, v in data.items()}, timeout=1200) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line.startswith("data:"):
                continue
            evt = json.loads(line[5:])
            if evt.get("type") == "token":
                text.append(evt["content"])
            elif evt.get("type") == "workspace":
                box = {"workspace": evt["workspace"], "tree": evt.get("tree")}
            elif evt.get("type") == "error":
                errors.append(str(evt.get("content")))
    return "".join(text), box, errors


def download(reply, pattern):
    match = re.search(r"\((/[^)\s]*" + pattern + r"[^)\s]*)\)", reply) or re.search(r'(/api/[^\s")]*' + pattern + r")", reply)
    return httpx.get(BASE + match.group(1), timeout=60).content if match else b""


def check_web(state):
    reply, box, errors = chat(WEB)
    if errors or not box:
        return errors or ["proje oluşmadı"]
    state.update(reply=reply, box=box)
    ws = WORKSPACES / box["workspace"]["id"]
    probe = workspace_web.probe(ws) or {"errors": ["tarayıcı testi çalışmadı"]}
    absent = spec_contract.missing(ws, spec_contract.extract(WEB))
    return list(probe["errors"]) + ([f"tarifte olup sayfada olmayan: {absent}"] if absent else [])


def check_revision(state):
    if "box" not in state:
        return ["web senaryosu olmadan çalışmaz"]
    history = [{"role": "user", "text": WEB}, {"role": "assistant", "text": state["reply"], "workspace": state["box"]}]
    reply, _box, errors = chat(CHANGE, history)
    page = (WORKSPACES / state["box"]["workspace"]["id"] / "index.html").read_text(encoding="utf-8")
    problems = errors + ([] if "#10b981" in page.lower() else ["yeni renk dosyada yok"])
    return problems + (["revizyon testi geçmedi"] if "GEÇMEDİ" in reply else [])


def check_api(_state):
    reply, box, errors = chat(API)
    if errors or not box:
        return errors or ["proje oluşmadı"]
    return ["çalıştırma testi geçmedi: " + reply[reply.find("TESTİ"):][:200]] if "TESTİ GEÇEMEDİ" in reply else []


def check_flow(_state):
    reply, _box, errors = chat(FLOW)
    svg = download(reply, r"\.svg") or (reply[reply.find("<svg"): reply.rfind("</svg>") + 6].encode() if "<svg" in reply else b"")
    if errors or not svg:
        return errors or ["SVG yok"]
    root = ET.fromstring(svg)
    labels = " ".join(t for t in root.itertext()).lower()
    return [] if "stok" in labels and "kargo" in labels else ["şemada istenen adımlar yok"]


def check_pdf(_state):
    import pymupdf

    reply, _box, errors = chat(PDF)
    blob = download(reply, r"\.pdf")
    if errors or not blob.startswith(b"%PDF"):
        return errors or ["geçerli PDF yok"]
    with pymupdf.open(stream=io.BytesIO(blob), filetype="pdf") as doc:
        text = "".join(page.get_text() for page in doc)
    return [] if len(text) > 400 and "enerji" in text.lower() else ["PDF metni boş ya da konu dışı"]


def check_image(_state):
    reply, _box, errors = chat(IMAGE)
    blob = download(reply, r"\.(?:svg|png)")
    ok = blob.startswith((b"<svg", b"<?xml", b"\x89PNG"))
    return errors or ([] if ok else ["geçerli görsel yok"])


SCENARIOS = {"web": check_web, "revision": check_revision, "api": check_api, "flow": check_flow, "pdf": check_pdf, "image": check_image}


def main(names):
    state, report, failures = {}, {}, 0
    for name in names or list(SCENARIOS):
        start = time.time()
        try:
            problems = SCENARIOS[name](state)
        except (httpx.HTTPError, OSError, ValueError, KeyError, ET.ParseError) as exc:
            problems = [f"{type(exc).__name__}: {exc}"]
        failures += bool(problems)
        report[name] = {"passed": not problems, "seconds": round(time.time() - start), "problems": [str(p)[:300] for p in problems]}
        print(name, "GEÇTİ" if not problems else "KALDI", report[name]["seconds"], "sn", report[name]["problems"], flush=True)
    (ROOT / "eval" / "reports" / "e2e_stress.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return failures


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
