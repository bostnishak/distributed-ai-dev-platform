"""v5 milestone 09 exit proof: grounded, cited answers from a scanned PDF, an ugly workbook and a spoken recording.

Usage: master/venv/Scripts/python.exe scripts/verify_milestone_09.py      (exit 0 only when every check passes)
Needs the OCR model (scripts/vendor_fetch.py), faster-whisper, the local Turkish voice and Ollama.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_TMP = tempfile.mkdtemp(prefix="m09_")
os.environ.update(DB_PATH=str(Path(_TMP) / "veri" / "platform.db"), WORKSPACES_DIR=str(Path(_TMP) / "veri" / "workspaces"))
sys.path.insert(0, str(ROOT / "master"))
sys.path.insert(0, str(ROOT / "master" / "tests"))

import inbox  # noqa: E402
import multimodal_samples as samples  # noqa: E402
import turkish  # noqa: E402

PROOF = ROOT / "eval" / "reports" / "milestone_09.json"
VOICE = ROOT / "master" / "data" / "voices" / "tr_TR-dfki-medium.onnx"
QUESTIONS = (
    ("taranmış PDF", "Depo teslim tutanağında şişe kapağı koli sayısı kaç?", ("1.250", "1250"), "tutanak.pdf, sayfa 1 (OCR"),
    ("dağınık Excel", "Sevkiyat listesinde Tutar sütununun toplamı kaç?", ("14711.25", "14.711,25", "14711,25"), "sevkiyat.xlsx, Satış"),
    ("ses kaydı", "Ses kaydına göre dolum makinesinin bakımı kaç saat sürecek ve sorumlusu kim?", ("mehmet",), "toplanti.wav, 00:"),
)


def code_tests() -> str:
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_v5_m09_multimodal.py"], cwd=ROOT / "master",
                          env={**os.environ, "PYTHONPATH": os.pathsep.join([".", "tests"])}, capture_output=True, text=True, encoding="utf-8", timeout=900)  # noqa: S603, RUF100
    assert done.returncode == 0 and "skipped" not in done.stdout.splitlines()[-1], done.stdout[-600:]
    return done.stdout.strip().splitlines()[-1]


def fill_inbox() -> str:
    target = inbox.folder()
    (target / "tutanak.pdf").write_bytes(samples.scanned_pdf())
    (target / "sevkiyat.xlsx").write_bytes(samples.messy_workbook())
    samples.speech(target / "toplanti.wav", VOICE)
    counts = {}
    for path in inbox.files():
        found = inbox.sources_of(path)
        assert found and found[0].place != "uyarı", f"{path.name} okunamadı: {found[:1]}"
        counts[path.name] = len(found)
    return f"üç dosya okundu: {counts}"


async def ask(question: str, expected: tuple[str, ...], place: str) -> str:
    reply = await inbox.answer(question, inbox._generate)
    flat = turkish.lower(reply)
    assert not reply.startswith("Doğrulanabilir bir yanıt üretemedim"), reply[:400]
    assert any(turkish.lower(value) in flat for value in expected), f"beklenen değer yok {expected}: {reply[:400]}"
    sources = reply.split("**Kaynaklar**", 1)
    assert len(sources) == 2 and place in sources[1], f"beklenen kaynak yeri yok ({place}): {reply[:500]}"
    return re.sub(r"\s+", " ", reply)[:300]


async def unanswerable() -> str:
    reply = await inbox.answer("Şirketin 2027 yılı reklam bütçesi kaç TL?", inbox._generate)
    assert "bulamadım" in reply.lower() or reply.startswith("Doğrulanabilir"), f"kaynakta olmayan bilgi uyduruldu: {reply[:300]}"
    return re.sub(r"\s+", " ", reply)[:160]


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

    loop = asyncio.new_event_loop()
    check("kod testleri", code_tests)
    check("dosyalar inbox'ta okunur", fill_inbox)
    for name, question, expected, place in QUESTIONS:
        check(f"kaynaklı yanıt: {name}", lambda q=question, e=expected, p=place: loop.run_until_complete(ask(q, e, p)))
    check("kaynakta olmayan soru uydurulmaz", lambda: loop.run_until_complete(unanswerable()))
    PROOF.parent.mkdir(parents=True, exist_ok=True)
    PROOF.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(r["ok"] for r in results)
    print(f"{passed}/{len(results)} geçti | kanıt: {PROOF}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
