"""Difficulty ladder L1-L5: how far up the platform still succeeds, each rung checked by code.

Usage: python scripts/ladder.py [--levels 1 2 3] [--seed N]    (needs the server on port 8000 and Ollama)
L1 a fact from the chat · L2 exact arithmetic over given data · L3 one function that passes hidden cases ·
L4 a single-page app with the requested controls · L5 a stored API that survives a restart.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "master"))

import golden  # noqa: E402

REPORT = ROOT / "eval" / "reports" / "ladder.json"
_BLOCK_RE = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL)


def l1_recall(rng: random.Random) -> None:
    code = f"{rng.randint(1000, 9999)}-{rng.choice('ABCDEFG')}"
    reply = golden.chat("Parça kodum neydi? Yalnız kodu yaz.", history=[{"role": "user", "text": f"Parça kodum {code}."}, {"role": "assistant", "text": "Tamam."}])
    golden.need(code in reply.text, "kod hatırlanmadı", reply.text)


def l2_arithmetic(rng: random.Random) -> None:
    rows = [(name, rng.randint(11, 97), rng.randint(3, 19)) for name in ("kalem", "defter", "silgi", "cetvel")]
    listing = "; ".join(f"{name}: {count} adet, tanesi {price} TL" for name, count, price in rows)
    total = sum(count * price for _name, count, price in rows)
    reply = golden.chat(f"Şu siparişin toplam tutarını hesapla: {listing}. Son satıra yalnız toplam sayıyı yaz.")
    golden.need(str(total) in golden.digits(reply.text), f"toplam {total} bulunamadı", reply.text[-200:])


def l3_function(rng: random.Random) -> None:
    step = rng.randint(2, 5)
    reply = golden.chat(f"Python'da `grupla(liste)` adında bir fonksiyon yaz: listeyi {step}'li parçalara bölsün ve parçaların listesini döndürsün; son parça kısa kalabilir. Yalnız kod ver.")
    block = _BLOCK_RE.search(reply.text)
    golden.need(block is not None, "kod bloğu yok", reply.text[:200])
    from sandbox import runner

    data = list(range(rng.randint(7, 19)))
    expected = [data[i : i + step] for i in range(0, len(data), step)]
    done = runner.run_python_code(f"{block.group(1)}\nassert grupla({data}) == {expected}\nassert grupla([]) == []\nprint('TAMAM')\n")
    golden.need(done.get("ok") and "TAMAM" in done.get("stdout", ""), "gizli durumlar geçmedi", str(done.get("stderr", ""))[-200:])


def l4_page(rng: random.Random) -> None:
    labels = rng.sample(["Ekle", "Temizle", "Sırala", "Say"], 2)
    reply = golden.chat(f"Tek HTML dosyalık bir alışveriş listesi yap; '{labels[0]}' ve '{labels[1]}' adlı düğmeler olsun.")
    golden.need(reply.workspace is not None, "proje oluşmadı", reply.text[-200:])
    import workspace_builder as wb

    page = (wb.safe_workspace_dir(reply.workspace["workspace"]["id"]) / "index.html").read_text(encoding="utf-8")
    golden.need(all(label in page for label in labels), "istenen düğmeler yok")


def l5_application(rng: random.Random) -> None:
    resource = rng.choice(["kitaplar", "gorevler", "notlar"])
    reply = golden.chat(f"FastAPI ve SQLite ile {resource} için API ve basit bir sayfa yap: GET ve POST /api/{resource} (201), DELETE /api/{resource}/{{id}}; kayıtlar yeniden başlatınca kalsın.")
    golden.need(reply.workspace is not None, "proje oluşmadı", reply.text[-200:])
    import done_gate
    import workspace_builder as wb

    status, detail = done_gate.server_proof(wb.safe_workspace_dir(reply.workspace["workspace"]["id"])) or ("yapılamadı", "sunucu projesi değil")
    golden.need(status == done_gate.PASSED, "canlı kanıt geçmedi", detail)


LEVELS: dict[int, Callable[[random.Random], None]] = {1: l1_recall, 2: l2_arithmetic, 3: l3_function, 4: l4_page, 5: l5_application}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--levels", nargs="*", type=int, default=list(LEVELS))
    parser.add_argument("--seed", type=int, default=int(time.time()) % 100000)
    args = parser.parse_args()
    results = []
    for level in args.levels:
        started = time.time()
        try:
            LEVELS[level](random.Random(f"{args.seed}-{level}"))
            ok, note = True, ""
        except Exception as exc:  # any failure of a rung is a failed rung
            ok, note = False, f"{type(exc).__name__}: {exc}"[:300]
        results.append({"level": level, "name": LEVELS[level].__name__, "ok": ok, "seconds": round(time.time() - started, 1), "note": note})
        print(f"{'GEÇTİ' if ok else 'KALDI'} L{level} {results[-1]['seconds']}s {note}", flush=True)
    reached = 0
    for row in sorted(results, key=lambda r: r["level"]):
        if not row["ok"] or row["level"] != reached + 1:
            break
        reached = row["level"]
    print(f"Kesintisiz çıkılan basamak: L{reached} | seed {args.seed}")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"seed": args.seed, "reached": reached, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
