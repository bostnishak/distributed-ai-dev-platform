"""v5 milestone 13 exit proof: a corrupt-and-restore drill, and a measured Pass@1 change from learned rules and snippets.

Usage: master/venv/Scripts/python.exe scripts/verify_milestone_13.py      (needs Ollama and Docker for the code sandbox)
Pass@1 is measured by running tests: the held-out tasks are solved once without and once with what was learned from
different training tasks. The check passes only when the number of first-try successes really goes up.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_TMP = tempfile.mkdtemp(prefix="m13_")
os.environ.update(DATA_DIR=str(Path(_TMP) / "veri"), DB_PATH=str(Path(_TMP) / "veri" / "platform.db"), WORKSPACES_DIR=str(Path(_TMP) / "veri" / "workspaces"))
sys.path.insert(0, str(ROOT / "master"))

import config  # noqa: E402
import failure_rules  # noqa: E402
import verified_tasks  # noqa: E402
import workspace_builder as wb  # noqa: E402
from verified_tasks import _task  # noqa: E402

PROOF = ROOT / "eval" / "reports" / "milestone_13.json"
MODEL = os.environ.get("PASS_MODEL", "qwen2.5-coder:7b")
TRAIN = (
    _task("tr_lower", "tr_lower(text) -> str: Türkçe kurallarıyla küçük harfe çevir.", "assert tr_lower('IŞIK İZMİR') == 'ışık izmir'", "assert len(tr_lower('İ')) == 1"),
    _task("tr_upper", "tr_upper(text) -> str: Türkçe kurallarıyla büyük harfe çevir.", "assert tr_upper('ışık izmir') == 'IŞIK İZMİR'"),
    _task("round_money", "round_money(value: str) -> str: ondalık metni iki haneye yarım yukarı yuvarla ('1.005' -> '1.01').", "assert round_money('1.005') == '1.01'", "assert round_money('2.675') == '2.68'", "assert round_money('3') == '3.00'"),
)
HELD_OUT = (
    _task("tr_title", "tr_title(text) -> str: Türkçe kurallarıyla her kelimenin ilk harfini büyük, kalanını küçük yap.", "assert tr_title('istanbul IŞIKLARI') == 'İstanbul Işıkları'", "assert tr_title('ıspanak İNCİR') == 'Ispanak İncir'"),
    _task("tr_equal", "tr_equal(a, b) -> bool: Türkçe büyük/küçük harf farkını yok sayarak iki metni karşılaştır.", "assert tr_equal('IĞDIR', 'ığdır')", "assert tr_equal('İzmir', 'izmir')", "assert not tr_equal('ışık', 'işik')"),
    _task("tr_count", "tr_count(text, letter) -> int: Türkçe büyük/küçük harf farkını yok sayarak harfin kaç kez geçtiğini say.", "assert tr_count('Iıİi', 'ı') == 2", "assert tr_count('Iıİi', 'İ') == 2"),
    _task("tr_initials", "tr_initials(name) -> str: ad soyaddan Türkçe büyük harfli baş harfleri döndür.", "assert tr_initials('ilker ışık') == 'İI'"),
    _task("vat_total", "vat_total(amount: str, rate: int) -> str: KDV dahil tutarı iki haneye yarım yukarı yuvarlayıp metin döndür.", "assert vat_total('0.1250', 0) == '0.13'", "assert vat_total('2.675', 0) == '2.68'", "assert vat_total('100', 20) == '120.00'"),
    _task("line_total", "line_total(quantity: int, price: str) -> str: adet çarpı birim fiyatı iki haneye yarım yukarı yuvarlayıp metin döndür.", "assert line_total(3, '0.335') == '1.01'", "assert line_total(5, '1.001') == '5.01'", "assert line_total(2, '4') == '8.00'"),
)


def code_tests() -> str:
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_v5_m13_recovery.py"], cwd=ROOT / "master",
                          env={**os.environ, "PYTHONPATH": "."}, capture_output=True, text=True, encoding="utf-8", timeout=600)  # noqa: S603, RUF100
    assert done.returncode == 0, done.stdout[-600:]
    return done.stdout.strip().splitlines()[-1]


def _ai_os(*args: str) -> str:
    done = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts" / "ai_os.py"), *args], env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                          capture_output=True, text=True, encoding="utf-8", timeout=600)  # noqa: S603, RUF100
    assert done.returncode == 0, f"{done.stdout[-500:]} {done.stderr[-500:]}"
    return done.stdout.strip()


def drill() -> str:
    root = Path(config.DATA_DIR)
    (root / "workspaces" / "p1").mkdir(parents=True)
    page = root / "workspaces" / "p1" / "index.html"
    page.write_text("<p>kanıt sayfası</p>", encoding="utf-8")
    conn = sqlite3.connect(root / "platform.db")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE bellek (metin TEXT)")
    conn.executemany("INSERT INTO bellek VALUES (?)", [(f"kayıt {i}",) for i in range(500)])
    conn.commit()
    conn.close()
    identifier = _ai_os("backup").split(": ")[1]
    assert identifier in _ai_os("backups")
    (root / "platform.db").write_bytes(os.urandom(8192))
    page.unlink()
    try:
        broken = sqlite3.connect(root / "platform.db")
        broken.execute("SELECT * FROM bellek").fetchall()
        raise AssertionError("veritabanı bozulmamış görünüyor")
    except sqlite3.DatabaseError:
        pass
    finally:
        broken.close()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    message = _ai_os("restore", identifier, "--port", str(port))
    conn = sqlite3.connect(root / "platform.db")
    rows = conn.execute("SELECT count(*) FROM bellek").fetchone()[0]
    conn.close()
    assert rows == 500 and page.read_text(encoding="utf-8") == "<p>kanıt sayfası</p>", f"{rows}"
    return f"veritabanı bozuldu, proje silindi; `ai-os restore {identifier}` ile 500 kayıt ve dosya geri geldi ({message.split('. ')[0]})"


async def _generate(system: str, user: str) -> str:
    return await wb._ollama_generate(MODEL, system, user, num_predict=200, temperature=0.1)


async def _round(tasks, learned: bool) -> dict[str, bool]:
    results = {}
    for task in tasks:
        code = await verified_tasks.solve(MODEL, task, failure_rules.hint(task.spec) if learned else "")
        results[task.name] = (await verified_tasks.passes(code, task.checks))[0]
    return results


async def _learn() -> tuple[int, int]:
    """From the training tasks only: a failure becomes a rule; a success, or a repaired solution, a snippet."""
    rules = snippets = 0
    for task in TRAIN:
        code = await verified_tasks.solve(MODEL, task)
        passed, log = await verified_tasks.passes(code, task.checks)
        for _attempt in range(3):
            if passed:
                break
            rules += bool(await failure_rules.mine(task.spec, log, _generate))
            code = await verified_tasks.solve(MODEL, task, f"\n\nÖnceki deneme testte başarısız oldu:\n{log[-700:]}\nDüzelt.")
            passed, log = await verified_tasks.passes(code, task.checks)
        if passed:
            failure_rules.keep_snippet(task.spec, code)
            snippets += 1
    return rules, snippets


def pass_at_one() -> str:
    async def run():
        before = await _round(HELD_OUT, learned=False)
        rules, snippets = await _learn()
        after = await _round(HELD_OUT, learned=True)
        return before, rules, snippets, after

    before, rules, snippets, after = asyncio.run(run())
    PROOF.parent.mkdir(parents=True, exist_ok=True)
    (PROOF.parent / "milestone_13_pass.json").write_text(json.dumps({"model": MODEL, "before": before, "after": after, "learned": failure_rules.load()}, ensure_ascii=False, indent=2), encoding="utf-8")
    first, second, total = sum(before.values()), sum(after.values()), len(HELD_OUT)
    summary = f"{MODEL}: görülmemiş {total} görevde Pass@1 {first}/{total} -> {second}/{total} ({rules} kural, {snippets} doğrulanmış parça öğrenildi)"
    assert second > first, summary + " (artış ölçülmedi)"
    return summary


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
    check("boz-geri yükle tatbikatı", drill)
    check("Pass@1 artışı (kural ve parça)", pass_at_one)
    PROOF.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(r["ok"] for r in results)
    print(f"{passed}/{len(results)} geçti | kanıt: {PROOF}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
