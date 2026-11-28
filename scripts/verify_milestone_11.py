"""v5 milestone 11 exit proof: four deliverables made at once agree to the last decimal, with pictures and no formula error.

Usage: master/venv/Scripts/python.exe scripts/verify_milestone_11.py      (needs LibreOffice and Chrome; no model)
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
_TMP = tempfile.mkdtemp(prefix="m11_")
os.environ.update(DB_PATH=str(Path(_TMP) / "veri" / "platform.db"), WORKSPACES_DIR=str(Path(_TMP) / "veri" / "workspaces"))
sys.path.insert(0, str(ROOT / "master"))

import config  # noqa: E402
import consistency  # noqa: E402
import consistency_files  # noqa: E402
import office_verify  # noqa: E402

PROOF = ROOT / "eval" / "reports" / "milestone_11.json"
COMMAND = ("tutarlı rapor: 2026 Kasım depo giderleri; koli 1250 x 4,375; palet streç filmi 37 x 189,99; termal etiket rulosu 4820 x 0,355; "
           "forklift aküsü 3 x 12480,50; yarım kuruş sınaması 3 x 0,335; kdv 20")


def code_tests() -> str:
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_v5_m11_consistency.py"], cwd=ROOT / "master",
                          env={**os.environ, "PYTHONPATH": "."}, capture_output=True, text=True, encoding="utf-8", timeout=900)  # noqa: S603, RUF100
    assert done.returncode == 0 and "skipped" not in done.stdout.splitlines()[-1], done.stdout[-600:]
    return done.stdout.strip().splitlines()[-1]


def _workspace() -> Path:
    return next(p for p in config.WORKSPACES_DIR.iterdir() if p.name.startswith("tutarli-rapor-"))


def chat_command() -> str:
    from chat_agents import fastpath

    async def read() -> str:
        response = fastpath(COMMAND, None)
        assert response is not None, "sohbet komutu tanınmadı"
        return "".join([chunk async for chunk in response.body_iterator])

    stream = asyncio.run(read())
    assert "son haneye kadar eşleşti" in stream and '"workspace"' in stream, stream[:800]
    return "sohbetten tek komutla dört dosya üretildi ve teslim edildi"


def agreement() -> str:
    folder = _workspace()
    report = consistency.parse(COMMAND.split(":", 1)[1])
    files = {kind: folder / name for kind, name in consistency_files.NAMES.items()}
    sources = consistency_files.read_all(report, files)
    differences = consistency.mismatches(consistency.figures(report), sources)
    assert not differences, str(differences)
    values = sum(len(v) for v in sources.values())
    return f"{len(sources)} okumada {values} değer SymPy sonucuyla son haneye kadar aynı; genel toplam {consistency.turkish(consistency.figures(report)[consistency.TOTAL])} TL"


def libreoffice_and_pictures() -> str:
    folder = _workspace()
    files = {kind: folder / name for kind, name in consistency_files.NAMES.items()}
    for kind in ("excel", "sunum"):
        problems = office_verify.check(files[kind])
        assert problems == [], f"{kind}: {problems}"
    pictures = consistency_files.render_pngs(files, PROOF.parent / "milestone_11_png")
    assert len(pictures) == 4, str(pictures)
    return "LibreOffice yeniden hesaplamasında hata yok; görsel kanıt: " + ", ".join(p.name for p in pictures)


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
    check("dörtlü üretim (sohbet komutu)", chat_command)
    check("dört dosya aynı sayıları gösterir", agreement)
    check("formül hatası yok, görsel kanıt", libreoffice_and_pictures)
    PROOF.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(r["ok"] for r in results)
    print(f"{passed}/{len(results)} geçti | kanıt: {PROOF}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
