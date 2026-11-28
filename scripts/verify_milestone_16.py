"""v5 milestone 16, the certification: every milestone proof, the whole test suite and the zero-cost rule, together.

Usage: master/venv/Scripts/python.exe scripts/verify_milestone_16.py [--skip 4 7 ...]
Runs for a long time (it drives real models, browsers and containers). Nothing is claimed for a skipped or failed part.
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
PROOF = ROOT / "eval" / "reports" / "milestone_16.json"
PAID = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY", "AZURE_OPENAI_API_KEY", "MISTRAL_API_KEY", "COHERE_API_KEY", "GROQ_API_KEY")
EXTRA_ENV = {8: {"MODEL": "1"}}


def zero_cost() -> tuple[bool, str]:
    """No paid provider is switched on and no paid key is configured for the platform."""
    sys.path.insert(0, str(ROOT / "master"))
    import config
    from gateway.providers import load_optional_cloud_providers

    keys = [name for name in PAID if os.environ.get(name)]
    enabled = sorted(load_optional_cloud_providers())
    local = config.OLLAMA_URL.startswith(("http://127.0.0.1", "http://localhost"))
    problems = [f"ücretli anahtar tanımlı: {', '.join(keys)}"] if keys else []
    problems += [f"bulut sağlayıcı açık: {', '.join(enabled)}"] if enabled else []
    problems += [] if local else [f"model adresi yerel değil: {config.OLLAMA_URL}"]
    return not problems, "; ".join(problems) or "bulut sağlayıcı kapalı, ücretli anahtar yok, modeller yerel Ollama'da"


def suite() -> tuple[bool, str]:
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"], cwd=ROOT / "master",
                          env={**os.environ, "PYTHONPATH": "."}, capture_output=True, text=True, encoding="utf-8", timeout=5400)  # noqa: S603, RUF100
    subprocess.run(["git", "checkout", "-q", "eval/reports/latest_benchmark.json"], cwd=ROOT, capture_output=True)  # noqa: S603, S607, RUF100
    return done.returncode == 0, (done.stdout.strip().splitlines() or ["çıktı yok"])[-1]


def milestone(number: int) -> tuple[bool, str]:
    script = ROOT / "scripts" / f"verify_milestone_{number:02d}.py"
    done = subprocess.run([sys.executable, "-X", "utf8", str(script)], cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8", **EXTRA_ENV.get(number, {})},
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5400)  # noqa: S603, RUF100
    lines = done.stdout.splitlines()
    summary = next((line for line in reversed(lines) if "geçti |" in line), (lines or [done.stderr[-200:]])[-1])
    failed = [line[:200] for line in lines if line.startswith("KALDI")]
    return done.returncode == 0, summary.split(" | ")[0] + (f" — {failed[0]}" if failed else "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip", nargs="*", type=int, default=[])
    parser.add_argument("--no-suite", action="store_true")
    options = parser.parse_args()
    results = []

    def record(name: str, outcome) -> None:
        started = time.time()
        try:
            ok, detail = outcome()
        except (subprocess.TimeoutExpired, OSError, ImportError, ValueError) as exc:
            ok, detail = False, f"{type(exc).__name__}: {exc}"[:400]
        results.append({"check": name, "ok": ok, "detail": detail, "seconds": round(time.time() - started, 1)})
        print(f"{'GEÇTİ' if ok else 'KALDI'} {name} ({results[-1]['seconds']} sn): {detail}", flush=True)
        PROOF.parent.mkdir(parents=True, exist_ok=True)
        PROOF.write_text(json.dumps({"results": results, "skipped": options.skip}, ensure_ascii=False, indent=2), encoding="utf-8")

    record("sıfır maliyet kuralı", zero_cost)
    if not options.no_suite:
        record("tüm testler (v1-v5)", suite)
    for number in range(1, 16):
        if number not in options.skip:
            record(f"M{number:02d} kanıtı", lambda n=number: milestone(n))
    passed = sum(r["ok"] for r in results)
    certified = passed == len(results) and not options.skip and not options.no_suite
    print(f"{passed}/{len(results)} geçti; {'SERTİFİKA: tam' if certified else 'sertifika verilmedi (kalan ya da atlanan var)'} | kanıt: {PROOF}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
