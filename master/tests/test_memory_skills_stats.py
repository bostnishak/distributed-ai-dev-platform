"""Bi-temporal memory, verified skill cards and release statistics."""

import pytest

import config
import eval_stats
import memory_engine
import memory_timeline
import skill_library

pytestmark = pytest.mark.unit


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "platform.db")
    monkeypatch.setattr(memory_engine, "_memory_db_path", lambda: tmp_path / "memory.db")
    return tmp_path


def test_overwritten_facts_stay_queryable_by_time(data):
    memory_timeline.install()
    memory_engine.upsert_semantic_fact("tercih", "veritabani", "SQLite")
    first = memory_timeline.history("veritabani")[0]["valid_from"]
    memory_engine.upsert_semantic_fact("tercih", "veritabani", "PostgreSQL")
    values = memory_timeline.history("veritabani")
    assert [v["fact_value"] for v in values] == ["SQLite", "PostgreSQL"] and values[0]["valid_to"] and values[1]["valid_to"] is None
    assert memory_timeline.as_of(first)["veritabani"] == "SQLite"
    assert memory_timeline.purge("veritabani") == 2 and memory_timeline.history("veritabani") == []


def test_only_similar_requests_get_a_reference(data):
    skill_library.add("FastAPI ile not tutma API projesi", ["app.py", "requirements.txt"])
    assert "app.py" in skill_library.reference("FastAPI ile görev tutma API projesi")
    assert skill_library.reference("kahve dükkanı logosu çiz") == ""


def test_statistics_reject_luck_and_regressions():
    assert eval_stats.mcnemar_exact([False] * 10, [True] * 10) < 0.01
    assert eval_stats.mcnemar_exact([True, False], [True, True]) == 1.0
    assert eval_stats.gate([True, False, False], [False, True, True])[0] is False
    assert eval_stats.gate([False] * 8, [True] * 8)[0] is True
    _low, high = eval_stats.bootstrap_difference([10.0, 12.0, 11.0], [5.0, 6.0, 5.5])
    assert high < 0
    assert eval_stats.sprt([True] * 20) == "accept" and eval_stats.sprt([False] * 8) == "reject" and eval_stats.sprt([True]) == "continue"
