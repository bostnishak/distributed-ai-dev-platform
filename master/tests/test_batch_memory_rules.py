"""Standing preferences, event history, reversible migrations, business-rule checks, variants and affected tests."""

import asyncio

import pytest

import event_log
import migration_check
import preferences
import property_check
import repo_map
import variants
import workspace_commands

pytestmark = pytest.mark.unit


def test_only_standing_statements_are_kept_and_newer_ones_replace_older(tmp_path, monkeypatch):
    monkeypatch.setattr(preferences, "_path", lambda user: tmp_path / "p.json")
    assert preferences.remember("Bu butonu mavi yap.") == ""
    assert preferences.remember("Bundan sonra gradyan kullanma.")
    assert preferences.remember("Her zaman koyu tema olsun.")
    assert preferences.remember("Bundan sonra gradyan kullan.")
    texts = [item["text"] for item in preferences.load()]
    assert texts == ["Her zaman koyu tema olsun.", "Bundan sonra gradyan kullan."]
    assert "koyu tema" in preferences.brief()
    assert "koyu tema" in preferences.command("tercihlerimi göster")
    assert "silindi" in preferences.command("tercihlerimi sil") and preferences.brief() == ""


def test_events_are_appended_in_order(tmp_path):
    event_log.record(tmp_path, "sürüm", "v1: ilk")
    event_log.record(tmp_path, "geri dönüş", "v1")
    assert [e["kind"] for e in event_log.read(tmp_path)] == ["sürüm", "geri dönüş"]


def test_migrations_must_round_trip(tmp_path):
    assert migration_check.check(tmp_path) is None
    (tmp_path / "001.up.sql").write_text("CREATE TABLE a (id INTEGER);", encoding="utf-8")
    (tmp_path / "001.down.sql").write_text("DROP TABLE a;", encoding="utf-8")
    assert migration_check.check(tmp_path) == []
    (tmp_path / "002.up.sql").write_text("CREATE TABLE b (id INTEGER);", encoding="utf-8")
    (tmp_path / "002.down.sql").write_text("SELECT 1;", encoding="utf-8")
    assert any("eski haline dönmüyor" in p for p in migration_check.check(tmp_path))


def test_business_rule_is_reported_with_its_counterexample(tmp_path):
    (tmp_path / "account.py").write_text("class Account:\n    balance = 0\n", encoding="utf-8")
    request = "Hesap uygulaması yaz. Bakiye asla negatif olamaz."
    assert property_check.rules(request) == ["Bakiye asla negatif olamaz"]

    async def writer(system, user):
        return "```python\nfrom hypothesis import given, strategies as st\n\n\n@given(st.integers())\ndef test_rule(x):\n    assert x >= 0\n```"

    broken = asyncio.run(property_check.report(tmp_path, request, [], writer, lambda *_: "Falsifying example: test_rule(\n    x=-1,\n)\nE assert -1 >= 0"))
    assert "İHLAL" in broken and "x=-1" in broken
    held = asyncio.run(property_check.report(tmp_path, request, [], writer, lambda *_: ""))
    assert "bozulmadı" in held and "kanıt değil" in held

    async def vanity(system, user):
        return "```python\ndef test_rule():\n    pass\n```"

    assert "denetlenemedi" in asyncio.run(property_check.report(tmp_path, request, [], vanity, lambda *_: ""))


def test_variants_differ_and_only_on_request():
    assert variants.parse("butonu mavi yap") == ""
    base = variants.parse("stok paneli yap, iki tasarım varyantı hazırla")
    first, second = variants.requests_for(base)
    assert "stok paneli" in first[1] and first[1] != second[1] and "--accent" in first[1]


def test_only_dependent_tests_are_selected(tmp_path):
    (tmp_path / "db.py").write_text("def connect():\n    return 1\n", encoding="utf-8")
    (tmp_path / "other.py").write_text("def other():\n    return 2\n", encoding="utf-8")
    (tmp_path / "test_db.py").write_text("from db import connect\n\ndef test_c():\n    assert connect()\n", encoding="utf-8")
    (tmp_path / "test_other.py").write_text("from other import other\n\ndef test_o():\n    assert other()\n", encoding="utf-8")
    assert repo_map.affected_tests(tmp_path, ["db.py"]) == ["test_db.py"]


def test_load_phrase_and_summary():
    assert workspace_commands.parse("yük testi yap") == ("load", "")
    assert workspace_commands.parse("yük testi nedir") is None
    text = workspace_commands.load_summary({"requests": 300, "workers": 10, "paths": ["/notes"], "rps": 900, "p50": 5, "p95": 9, "p99": 12, "errors": 0})
    assert "900" in text and "5 / 9 / 12" in text


def test_a_broken_property_test_is_rewritten_once(tmp_path):
    (tmp_path / "account.py").write_text("class Account:\n    pass\n", encoding="utf-8")
    asked = []

    async def writer(system, user):
        asked.append(user)
        return "```python\nfrom hypothesis import given, strategies as st\n\n\n@given(st.integers())\ndef test_rule(x):\n    assert x == x\n```"

    logs = iter(["E   hypothesis.errors.HypothesisException: bad", ""])
    out = asyncio.run(property_check.report(tmp_path, "Bakiye asla negatif olamaz.", [], writer, lambda *_: next(logs)))
    assert len(asked) == 2 and "HypothesisException" in asked[1] and "bozulmadı" in out
