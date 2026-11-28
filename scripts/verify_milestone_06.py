"""v5 milestone 06 exit proof: a live torture run catches an injected float-money bug, a double submit and Turkish İ/ı search.

Usage: python scripts/verify_milestone_06.py      (exit 0 only when every check passes; needs Docker and Chrome, no model)
Each application really runs in its own container on SQLite; the browser is real and the network faults are injected.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
_TMP = tempfile.mkdtemp(prefix="m06_")
os.environ.update(DB_PATH=str(Path(_TMP) / "veri" / "platform.db"), WORKSPACES_DIR=str(Path(_TMP) / "veri" / "workspaces"))
sys.path.insert(0, str(ROOT / "master"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "master" / "tests"))

from torture_sample import BUGS, app_source  # noqa: E402

import live_server  # noqa: E402
import torture  # noqa: E402

PROOF = ROOT / "eval" / "reports" / "milestone_06.json"
TABLE: dict[str, dict[str, str]] = {}


def code_tests() -> str:
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_v5_m06_torture.py"], cwd=ROOT / "master",
                          env={**os.environ, "PYTHONPATH": "."}, capture_output=True, text=True, encoding="utf-8", timeout=900)  # noqa: S603, RUF100
    assert done.returncode == 0, done.stdout[-600:]
    return done.stdout.strip().splitlines()[-1]


def _serve(bug: str):
    folder = Path(_TMP) / (bug or "dogru").replace(" ", "_").replace("/", "_")
    folder.mkdir()
    (folder / "app.py").write_text(app_source(bug), encoding="utf-8")
    (folder / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")
    return live_server.serve(folder)


def _tortured(url: str, checks: dict) -> dict:
    results = torture.run(url, checks)
    assert results is not None, "tarayıcı başlatılamadı"
    return results


def correct_application() -> str:
    with _serve("") as server:
        results = _tortured(server.url, {**torture.QUICK, **torture.NETWORK})
        results["50 tekrarda sızıntı"] = torture.leaks(server.url)
        results["50 yazmada sunucu belleği"] = torture.server_growth(server.url + "/api/kalemler", server.name, lambda n: httpx.post(server.url + "/api/kalemler", json={"metin": f"yük-{n}", "tutar": 1}, timeout=30).raise_for_status())
        before = httpx.get(server.url + "/api/kalemler", timeout=10).json()
        server.restart()
        after = httpx.get(server.url + "/api/kalemler", timeout=10).json()
    assert before and after == before, f"yeniden başlatınca veri değişti: {len(before)} -> {len(after)}"
    TABLE["doğru uygulama"] = {name: f"{'geçti' if passed else 'uygulanmaz' if passed is None else 'KALDI'} {detail}".strip() for name, (passed, detail) in results.items()}
    assert not torture.failures(results), "doğru uygulama kaldı: " + "; ".join(torture.failures(results))
    judged = sum(passed is True for passed, _ in results.values())
    return f"{judged} denetim geçti, {len(results) - judged} uygulanmaz; {len(after)} kayıt yeniden başlatmadan sağ çıktı"


def injected(bug: str, check: str) -> str:
    with _serve(bug) as server:
        passed, detail = _tortured(server.url, {check: {**torture.QUICK, **torture.NETWORK}[check]})[check]
    assert passed is False, f"enjekte hata yakalanmadı ({check}: {passed} {detail})"
    return detail


def scale_and_empty() -> str:
    folder = Path(_TMP) / "olcek"
    folder.mkdir()
    from test_v5_m06_torture import GOOD

    (folder / "index.html").write_text(GOOD, encoding="utf-8")
    results = _tortured((folder / "index.html").as_uri(), {**torture.HEAVY, "boş durum": torture.QUICK["boş durum"]})
    assert not torture.failures(results), "; ".join(torture.failures(results))
    return results["1000 kayıt"][1]


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

    check("kod testleri", code_tests)
    check("doğru uygulama tüm zorlamalardan geçer", correct_application)
    for bug, name in BUGS.items():
        check(f"enjekte hata yakalanır: {bug}", lambda b=bug, n=name: injected(b, n))
    check("1000 kayıt ve boş durum", scale_and_empty)
    PROOF.parent.mkdir(parents=True, exist_ok=True)
    PROOF.write_text(json.dumps({"results": results, "table": TABLE}, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(r["ok"] for r in results)
    print(f"{passed}/{len(results)} geçti | kanıt: {PROOF}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
