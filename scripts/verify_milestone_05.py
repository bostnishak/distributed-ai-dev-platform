"""v5 milestone 05 exit proof: an injected repair oscillation and a parallel write conflict are resolved without deadlock.

Usage: python scripts/verify_milestone_05.py      (exit 0 only when every check passes; needs Docker, no model)
The failures are real: a project whose own test fails in the sandbox, repair answers that swing between two wrong
versions (the injected part), and separate processes of work writing the same files at once.
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
_TMP = tempfile.mkdtemp(prefix="m05_")
os.environ.update(DB_PATH=str(Path(_TMP) / "veri" / "platform.db"), WORKSPACES_DIR=str(Path(_TMP) / "veri" / "workspaces"))
sys.path.insert(0, str(ROOT / "master"))

import budgets  # noqa: E402
import build_dag  # noqa: E402
import dag  # noqa: E402
import run_control  # noqa: E402
import workspace_builder as wb  # noqa: E402
import workspace_docker  # noqa: E402
import workspace_smoke  # noqa: E402
import write_lease  # noqa: E402

PROOF = ROOT / "eval" / "reports" / "milestone_05.json"


def code_tests() -> str:
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_v5_m05_governance.py"], cwd=ROOT / "master",
                          env={**os.environ, "PYTHONPATH": "."}, capture_output=True, text=True, encoding="utf-8", timeout=600)  # noqa: S603, RUF100
    assert done.returncode == 0, done.stdout[-600:]
    return done.stdout.strip().splitlines()[-1]


async def live_oscillation() -> str:
    """A project that crashes in the real sandbox, repaired with answers that go A -> B -> A -> B."""
    assert workspace_docker.available(), "Docker gerekli"
    ws_dir = Path(_TMP) / "salinim"
    ws_dir.mkdir()
    state_a = 'def toplam(a, b):\n    return a + c\n\n\nprint(toplam(1, 2))\n'
    state_b = 'def toplam(a, b):\n    return a + d\n\n\nprint(toplam(1, 2))\n'
    (ws_dir / "main.py").write_text(state_a, encoding="utf-8")
    answers = [state_b, state_a, state_b, state_a, state_b]
    calls: list[str] = []

    async def regenerate(_rel: str, ask: str) -> str:
        calls.append(ask)
        return f"```python\n{answers[len(calls) - 1]}```"

    started, last = time.time(), {}
    async for event in workspace_smoke.smoke_and_repair(ws_dir, regenerate, rounds=5):
        last = event
    final = (ws_dir / "main.py").read_text(encoding="utf-8")
    assert last.get("type") == "smoke" and last["ok"] is False, f"bozuk proje geçti sayıldı: {last}"
    assert len(calls) == 3, f"salınım kesilmedi: {len(calls)} onarım istendi"
    assert "TEKRARLAMA" in calls[2], "yasak listesi temiz bağlama taşınmadı"
    return f"5 turluk hakkın 3'ünde durduruldu ({time.time() - started:.1f} sn); dosya: {'B' if 'a + d' in final else 'A'} durumunda bırakıldı"


async def live_write_conflict() -> str:
    """Two runs write the same shared file and each its own function of one module, all at once, on disk."""
    ws_dir = Path(_TMP) / "cakisma"
    ws_dir.mkdir()
    (ws_dir / "m.py").write_text("def f():\n    return 0\n\n\ndef g():\n    return 0\n", encoding="utf-8")
    overlapping, active = [], set()

    def work_for(owner: str):
        def make(spec: dict):
            async def work(_record: dict) -> str:
                key = spec["path"]
                overlapping.extend([key] if key in active else [])
                active.add(key)
                before = (ws_dir / key).read_text(encoding="utf-8") if (ws_dir / key).is_file() else ""
                await asyncio.sleep(0.3)  # the width of a model call: without the lease the other writer would overwrite this line
                (ws_dir / key).write_text(before + owner + "\n", encoding="utf-8")
                active.discard(key)
                return owner

            return work

        return make

    async def run(owner: str) -> None:
        live = run_control.start(f"m05 {owner}", "cakisma")
        governed = build_dag._governed(ws_dir, budgets.run_budget(owner), work_for(owner))
        nodes = [dag.Node(name, governed({"path": name}), title=name) for name in ("package.json", "requirements.txt")]
        async for _event in dag.execute(live, nodes, 2):
            pass

    await asyncio.wait_for(asyncio.gather(run("birinci"), run("ikinci"), write_lease.write_symbol(ws_dir, "birinci", "m.py::f", "def f():\n    return 1"),
                                          write_lease.write_symbol(ws_dir, "ikinci", "m.py::g", "def g():\n    return 2")), 30)
    for name in ("package.json", "requirements.txt"):
        lines = sorted((ws_dir / name).read_text(encoding="utf-8").split())
        assert lines == ["birinci", "ikinci"], f"{name}: bir yazarın işi kayboldu: {lines}"
    module = (ws_dir / "m.py").read_text(encoding="utf-8")
    assert "return 1" in module and "return 2" in module and not overlapping and not write_lease.TABLE.held
    return "iki koşu aynı iki dosyaya ve aynı modülün iki fonksiyonuna eşzamanlı yazdı; kayıp yok, kilitlenme yok, kira kalmadı"


async def live_budget_rollback() -> str:
    """A real edit run whose writer stalls: the step is cancelled and the project is as before."""
    os.environ["BUDGET_STEP_SECONDS"] = "2"
    ws_dir = Path(_TMP) / "butce"
    ws_dir.mkdir()
    (ws_dir / "a.txt").write_text("birinci sürüm", encoding="utf-8")
    (ws_dir / "b.txt").write_text("ikinci", encoding="utf-8")

    async def write(target_dir: Path, _model: str, spec: dict, _ask: str) -> str:
        if spec["path"] == "b.txt":
            await asyncio.sleep(60)
        (target_dir / spec["path"]).write_text("değişti", encoding="utf-8")
        return "değişti"

    original, wb._generate_and_write_file = wb._generate_and_write_file, write
    started = time.time()
    try:
        async for _event in build_dag.edit_files(ws_dir, "değiştir", "yok", [{"path": "a.txt"}, {"path": "b.txt"}], lambda _s, ask: ("", ask)):
            pass
    except budgets.BudgetExceeded as exc:
        assert (ws_dir / "a.txt").read_text(encoding="utf-8") == "birinci sürüm", "tamamlanan dosya geri alınmadı"
        return f"{time.time() - started:.1f} sn'de durduruldu ve geri alındı: {exc}"
    finally:
        wb._generate_and_write_file = original
        os.environ.pop("BUDGET_STEP_SECONDS")
    raise AssertionError("bütçe aşımı fark edilmedi")


def main() -> int:
    results = []

    def check(name: str, run) -> None:
        started = time.time()
        try:
            ok, detail = True, str(run())
        except Exception as exc:  # noqa: BLE001, RUF100  # any failure of a check is a failed check
            ok, detail = False, f"{type(exc).__name__}: {exc}"[:800]
        results.append({"check": name, "ok": ok, "detail": detail, "seconds": round(time.time() - started, 1)})
        print(f"{'GEÇTİ' if ok else 'KALDI'} {name} ({results[-1]['seconds']} sn): {detail}", flush=True)

    check("kod testleri", code_tests)
    check("enjekte salınım canlı kum havuzunda kesildi", lambda: asyncio.run(live_oscillation()))
    check("eşzamanlı yazma çakışması", lambda: asyncio.run(live_write_conflict()))
    check("bütçe aşımında geri dönüş", lambda: asyncio.run(live_budget_rollback()))
    PROOF.parent.mkdir(parents=True, exist_ok=True)
    PROOF.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(r["ok"] for r in results)
    print(f"{passed}/{len(results)} geçti | kanıt: {PROOF}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
