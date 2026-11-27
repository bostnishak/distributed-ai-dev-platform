"""v5 milestone 04 exit proof: a request with 15+ constraints, built by a 7B model, meets every requirement.

Usage: python scripts/verify_milestone_04.py      (exit 0 only when every check passes; needs Ollama and Chrome)
Real model, real token stream, real browser. SLICE_MODEL picks the writer (default qwen2.5-coder:7b).
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
_TMP = tempfile.mkdtemp(prefix="m04_")
os.environ.update(DB_PATH=str(Path(_TMP) / "veri" / "platform.db"), WORKSPACES_DIR=str(Path(_TMP) / "veri" / "workspaces"))
os.environ.setdefault("SLICE_MODEL", "qwen2.5-coder:7b")
sys.path.insert(0, str(ROOT / "master"))

import agent_contracts  # noqa: E402
import critic_models  # noqa: E402
import gateway  # noqa: E402
import req_checks  # noqa: E402
import req_ledger  # noqa: E402
import slice_build  # noqa: E402
import workspace_builder as wb  # noqa: E402
from gateway import stream_guard  # noqa: E402
from prompt_loader import load_prompt  # noqa: E402

PROOF = ROOT / "eval" / "reports" / "milestone_04.json"
REQUEST = (
    "Tek sayfalık bir görev panosu yap. Renkler aynen: #0F172A arka plan, #38BDF8 vurgu, #F8FAFC yazı. "
    'Üst bar 64px yüksekliğinde ve başlığı "Görev Panosu"; solda 240px genişliğinde yan menü, ortada ana alan, altta alt bilgi. '
    'Ana alanda yer tutucusu "Yeni görev" olan bir girdi, "Ekle" düğmesi (yazılan görevi listeye ekler), '
    '"Temizle" düğmesi (tüm görevleri siler) ve "Tümü" düğmesi (tüm görevleri gösterir). '
    "Görevler sayfa yenilenince de kalsın (localStorage). Boş girdi eklenmesin. Mobil görünümde taşma olmasın. "
    "Harici kütüphane kullanma, alert kullanma."
)


def code_tests() -> str:
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_v5_m04_prosthetics.py"], cwd=ROOT / "master",
                          env={**os.environ, "PYTHONPATH": "."}, capture_output=True, text=True, encoding="utf-8", timeout=600)  # noqa: S603, RUF100
    assert done.returncode == 0, done.stdout[-600:]
    return done.stdout.strip().splitlines()[-1]


async def watchdog_live(model: str) -> str:
    """A real model is made to loop (repeat penalty below 1); the guard must cut the stream long before the token limit."""
    started, restart, after, finished = time.time(), None, [], False
    provider = gateway.default_client._get_provider("ollama")
    ask = [{"role": "user", "content": "Write the numbers from 1 to 500, separated by spaces."}]
    options = {"temperature": 0.0, "repeat_penalty": 0.5, "repeat_last_n": 512, "num_predict": 1500, "num_ctx": 4096}
    async for event in stream_guard.watched(provider, model, ask, options, 300.0):
        if event.get("type") == "restart":
            restart = restart or event
            after = []
        elif event.get("type") == "token":
            after.append(event.get("content") or "")
        finished = finished or event.get("type") == "done"
    assert restart is not None, "döngü kesilmedi: " + "".join(after)[-160:]
    assert finished and restart["chars"] < 2000, str(restart)
    return f"gerçek döngü {restart['chars']} karakterde kesildi ({restart['reason']}), yeniden denendi; toplam {time.time() - started:.1f} sn"


async def many_constraints(model: str) -> str:
    contract = await agent_contracts.intake(REQUEST)
    ledger = req_ledger.build(contract.model_dump(), REQUEST)
    assert len(ledger) >= 15, f"defterde yalnız {len(ledger)} koşul var:\n{req_ledger.listing(ledger)}"
    ws_dir = Path(_TMP) / "pano"

    def writer(temperature: float):
        async def generate(system: str, user: str) -> str:
            return await wb._ollama_generate(model, system, user, num_predict=7000, temperature=temperature)

        return generate

    await slice_build.build((ws_dir, REQUEST + agent_contracts.writer_notes(contract), load_prompt("b4_single_file_writer.txt")), ledger, writer(0.2), writer(0.1))
    verdicts = await asyncio.to_thread(req_checks.evaluate, ws_dir, ledger)  # judged again, independently of the build loop
    met, decidable = req_checks.score(verdicts)
    history = json.loads((ws_dir / slice_build.REPORT).read_text(encoding="utf-8"))["history"]
    (PROOF.parent / "milestone_04_page.html").write_text((ws_dir / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps(history, ensure_ascii=False))
    assert decidable == len(ledger) and met == decidable, f"{met}/{decidable} ({len(ledger)} koşul)\n" + "\n".join(req_checks.unmet(ledger, verdicts))
    return f"{model}: {met}/{len(ledger)} koşul karşılandı"


def other_family(loop: asyncio.AbstractEventLoop, model: str) -> str:
    critic = loop.run_until_complete(critic_models.critic_for(model))
    assert critic_models.family(critic) != critic_models.family(model), "başka aileden model kurulu değil"
    return f"yazan {model}, eleştiren {critic}"


def main() -> int:
    model = os.environ["SLICE_MODEL"]
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
    loop = asyncio.new_event_loop()
    check("kod testleri", code_tests)
    check("akış bekçisi gerçek modelde", lambda: loop.run_until_complete(watchdog_live(model)))
    check("eleştiri başka model ailesinden", lambda: other_family(loop, model))
    check("15+ koşullu istek küçük modelde %100", lambda: loop.run_until_complete(many_constraints(model)))
    PROOF.write_text(json.dumps({"model": model, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(r["ok"] for r in results)
    print(f"{passed}/{len(results)} geçti | kanıt: {PROOF}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
