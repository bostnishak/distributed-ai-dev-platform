"""v5 milestone 15: the burn-in harness on the real platform.

Usage: master/venv/Scripts/python.exe scripts/verify_milestone_15.py [--minutes 10] [--model]
A short run proves the harness and the platform under mixed load and injected faults. The specification asks for a
multi-hour run; start that on purpose with `python scripts/ai_os.py soak --hours 4` - it is not claimed here.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "master"))

import soak  # noqa: E402

PROOF = ROOT / "eval" / "reports" / "milestone_15.json"


def code_tests() -> str:
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_v5_m15_soak.py"], cwd=ROOT / "master",
                          env={**os.environ, "PYTHONPATH": "."}, capture_output=True, text=True, encoding="utf-8", timeout=900)  # noqa: S603, RUF100
    assert done.returncode == 0, done.stdout[-600:]
    return done.stdout.strip().splitlines()[-1]


def burn_in(minutes: float, model: bool) -> str:
    report = soak.soak(minutes / 60, model=model, out=PROOF.parent / "milestone_15_soak.json")
    assert not report["problems"], "; ".join(report["problems"][:6])
    return (f"{minutes:g} dk, {'modelli' if model else 'modelsiz'}: {sum(report['tasks'].values())} iş ({report['tasks']}); en yüksek bellek {report['peak_rss_mb']} MB, "
            f"bellek artışı %{(report['memory_growth'] or 0) * 100:.1f}; artık süreç/port yok, kilit ve bellek hatası yok")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=float, default=10.0)
    parser.add_argument("--model", action="store_true", help="include model tasks (uses the graphics card)")
    options = parser.parse_args()
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
    check("karışık yük ve arıza enjeksiyonu altında kısa yakma testi", lambda: burn_in(options.minutes, options.model))
    PROOF.write_text(json.dumps({"results": results, "minutes": options.minutes, "model": options.model, "multi_hour": options.minutes >= 120}, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(r["ok"] for r in results)
    print(f"{passed}/{len(results)} geçti | kanıt: {PROOF}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
