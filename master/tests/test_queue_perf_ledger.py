"""Priority queue, performance summary, tool scopes, verification ledger and repair preference pairs."""

import asyncio

import pytest

import ledger
import perf_report
import policy
import repair_pairs
from gateway import priority_gate

pytestmark = pytest.mark.unit


def test_interactive_calls_overtake_waiting_background_work():
    async def run():
        gate = priority_gate.PriorityGate(1)
        order = []

        async def job(name, feature):
            async with gate.slot(feature):
                order.append(name)
                await asyncio.sleep(0.01)

        first = asyncio.create_task(job("running", "chat"))
        await asyncio.sleep(0)
        waiting = [asyncio.create_task(job(n, f)) for n, f in (("night", "self_eval"), ("fix", "debugger"), ("user", "chat"), ("user2", "chat"))]
        await asyncio.gather(first, *waiting)
        return order

    assert asyncio.run(run()) == ["running", "user", "user2", "fix", "night"]


def test_a_cancelled_waiter_does_not_lose_the_slot():
    async def run():
        gate = priority_gate.PriorityGate(1)
        await gate.acquire(0)
        waiter = asyncio.create_task(gate.acquire(0))
        await asyncio.sleep(0)
        waiter.cancel()
        gate.release()
        await asyncio.wait_for(gate.acquire(0), 1)
        return True

    assert asyncio.run(run())


def test_performance_summary_per_model():
    rows = [{"model": "a", "feature": "chat", "tokens_out": 100, "latency_ms": 2000, "status": "ok"},
            {"model": "a", "feature": "chat", "tokens_out": 300, "latency_ms": 2000, "status": "ok"},
            {"model": "a", "feature": "x", "tokens_out": 0, "latency_ms": 0, "status": "error"}]
    (item,) = perf_report.summarise(rows, "model")
    assert item["calls"] == 3 and item["errors"] == 1 and item["tokens_per_s"] == 100.0 and item["total_s"] == 4


@pytest.mark.parametrize(("name", "scope"), [
    ("search_issues", "read"), ("get_user", "read"), ("createIssue", "write"), ("delete_file", "write"), ("repo.merge_pull_request", "write"), ("list_updates", "read"),
])
def test_tool_scope_from_the_name(name, scope):
    assert policy.tool_scope(name) == scope


def test_ledger_buckets(tmp_path):
    entry = ledger.build({"güvenlik": "", "yerleşim": None, "kod": ["x.py:1 hata"]})
    ledger.write(tmp_path, entry)
    ledger.assume(tmp_path, ledger.assumption_lines(["Intake ajanı", "Varsayım (doğrulanmadı): veriler yerelde kalacak"]))
    stored = ledger.read(tmp_path)
    assert stored["verified"] == ["güvenlik: sorun bulunmadı"] and stored["assumed"] == ["veriler yerelde kalacak"]
    assert stored["open"] == ["yerleşim: çalıştırılamadı", "x.py:1 hata"]


def test_repair_pairs_keep_only_changed_files_without_secrets(tmp_path, monkeypatch):
    monkeypatch.setattr(repair_pairs, "_path", lambda: tmp_path / "pairs.jsonl")
    key = "sk-" + "q" * 30
    written = repair_pairs.record("E assert", {"a.py": f"KEY='{key}'\nx=1\n", "b.py": "same\n"}, {"a.py": "x=2\n", "b.py": "same\n"})
    (pair,) = repair_pairs.load()
    assert written == 1 and pair["chosen"] == "x=2\n" and key not in pair["rejected"] and "a.py" in pair["prompt"]
