"""v5 milestone 05: swarm governance (frozen spec, oscillation breaker, write leases, budgets)."""

from __future__ import annotations

import asyncio
import json

import pytest

import budgets
import oscillation
import req_ledger
import spec_pointer
import write_lease

pytestmark = pytest.mark.unit

_CONTRACT = {"colors": ["#101010"], "labels": ["Başlık"], "buttons": [{"label": "Ekle", "behavior": "ekler"}], "endpoints": [{"method": "GET", "path": "/api/x"}]}


def test_each_writer_gets_the_frozen_spec_and_only_its_own_requirements(tmp_path):
    ledger = req_ledger.build(_CONTRACT, "")
    sha = spec_pointer.freeze(tmp_path, "istek", ledger)
    assert spec_pointer.freeze(tmp_path, "başka istek", ()) == sha, "ikinci yazım sözleşmeyi değiştirmez"
    assert spec_pointer.load(tmp_path)["request"] == "istek"
    css, server = spec_pointer.pointer(tmp_path, "css/a.css", ledger), spec_pointer.pointer(tmp_path, "app.py", ledger)
    assert "#101010" in css and "/api/x" not in css and "Ekle" not in css
    assert "/api/x" in server and "#101010" not in server and sha[:12] in server
    assert spec_pointer.pointer(tmp_path, "README.md", ledger) == ""
    target = tmp_path / spec_pointer.SPEC
    data = json.loads(target.read_text(encoding="utf-8"))
    data["requirements"] = []
    target.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="sonradan değiştirilmiş"):
        spec_pointer.load(tmp_path)


def test_oscillation_is_judged_by_meaning_and_halts_the_second_time():
    tracker = oscillation.Tracker()
    first, second = "def f():\n    return 1\n", "def f():\n    return 2\n"
    assert tracker.repeats("a.py", first, second) is False
    assert tracker.repeats("a.py", second, "# açıklama\ndef f():\n\n    return 1\n") is True
    assert tracker.halted is False
    assert tracker.repeats("a.py", second, second) is True and tracker.halted
    js = oscillation.canonical("a.js", "let a = 1; // x")
    assert js == oscillation.canonical("a.js", "/* y */ let a=1;") != oscillation.canonical("a.js", "let a=2;")
    assert oscillation.canonical("a.js", 'u = "https://a"') != oscillation.canonical("a.js", 'u = "https://b"')


def test_leases_collide_by_file_and_symbol():
    assert write_lease.collides("a.py", "A.py::f") and write_lease.collides("a.py::f", "a.py::f")
    assert not write_lease.collides("a.py::f", "a.py::g") and not write_lease.collides("a.py", "b.py")
    table = write_lease.Table()
    assert table.try_acquire("x", ["a.py", "b.py"])
    assert not table.try_acquire("y", ["c.py", "b.py"]) and "c.py" not in table.held, "ya hepsi ya hiçbiri"
    table.release("x")
    assert table.try_acquire("y", ["c.py", "b.py"])


def test_crossed_writers_finish_without_deadlock_and_a_stuck_one_is_named():
    table, order = write_lease.Table(), []

    async def writer(name, resources):
        async with table.lease(name, resources):
            order.append(f"{name}+")
            await asyncio.sleep(0.02)
            order.append(f"{name}-")

    async def run():
        await asyncio.wait_for(asyncio.gather(writer("bir", ["a", "b"]), writer("iki", ["b", "a"])), 5)
        async with table.lease("tutan", ["a"]):
            with pytest.raises(write_lease.LeaseTimeout, match="tutan"):
                async with table.lease("bekleyen", ["a"], wait_s=0.05):
                    pass

    asyncio.run(run())
    assert order in (["bir+", "bir-", "iki+", "iki-"], ["iki+", "iki-", "bir+", "bir-"])


def test_parallel_symbol_writers_do_not_undo_each_other(tmp_path):
    (tmp_path / "m.py").write_text("import os\n\n\ndef f():\n    return 0\n\n\ndef g():\n    return 0\n", encoding="utf-8")

    async def run():
        await asyncio.gather(
            write_lease.write_symbol(tmp_path, "bir", "m.py::f", "def f():\n    return 1"),
            write_lease.write_symbol(tmp_path, "iki", "m.py::g", "def g():\n    return 2"),
        )

    asyncio.run(run())
    text = (tmp_path / "m.py").read_text(encoding="utf-8")
    assert "return 1" in text and "return 2" in text and text.startswith("import os")
    with pytest.raises(ValueError):
        write_lease.replace_symbol(tmp_path / "m.py", "yok", "def yok(): pass")


def test_budgets_are_hierarchical_and_a_stalled_step_is_cancelled():
    run = budgets.Budget("koşu", 100, 60.0, 3)
    step = run.child("adım")
    with budgets.active(step):
        budgets.spend(tokens=60, attempts=2)
        assert run.used_tokens == 60 and run.used_attempts == 2
        with pytest.raises(budgets.BudgetExceeded, match="koşu"):
            budgets.spend(tokens=60)
    budgets.spend(tokens=10**9)  # no budget in force: free

    cancelled = []

    async def stalls():
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            cancelled.append(True)
            raise

    with pytest.raises(budgets.BudgetExceeded, match="durduruldu"):
        asyncio.run(budgets.within(budgets.Budget("adım", 10, 0.05, 1), stalls()))
    assert cancelled == [True]


def test_over_budget_change_leaves_the_project_as_it_was(tmp_path):
    import build_dag

    (tmp_path / "a.txt").write_text("eski", encoding="utf-8")

    async def events():
        (tmp_path / "a.txt").write_text("yarım", encoding="utf-8")
        (tmp_path / "yeni.txt").write_text("yeni", encoding="utf-8")
        yield "start", "a.txt", None
        raise budgets.BudgetExceeded("koşu: süre bütçesi aşıldı")

    async def run():
        async for _event in build_dag._rolled_back(tmp_path, {"a.txt": "eski", "yeni.txt": ""}, events()):
            pass

    with pytest.raises(budgets.BudgetExceeded):
        asyncio.run(run())
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "eski" and not (tmp_path / "yeni.txt").exists()


def test_repair_that_swings_back_is_refused(tmp_path):
    import workspace_smoke

    target = tmp_path / "app.py"
    good, other = "x = 1\n", "x = 2\n"
    target.write_text(good, encoding="utf-8")
    replies = iter([other, good, good])
    asked: list[str] = []

    async def regenerate(rel, ask):
        asked.append(ask)
        return f"```python\n{next(replies)}```"

    memory = workspace_smoke._RepairMemory()

    async def run():
        for _ in range(3):
            await workspace_smoke._fix_once(tmp_path.resolve(), target.resolve(), "hata", regenerate, memory)

    asyncio.run(run())
    assert target.read_text(encoding="utf-8").strip() == "x = 2", "eski duruma dönen yama yazılmaz"
    assert memory.tracker.halted
    assert "DENENİP BAŞARISIZ" in asked[2]
