"""Pinned constraints, the exact cache, the anonymiser and steering a resumed build."""

import asyncio
import json

import pytest

import checkpoint
import context_pins
import escalation
import exact_cache
import memory_engine

pytestmark = pytest.mark.unit


def test_first_turn_rules_survive_a_long_conversation():
    first = {"role": "user", "content": "Ana renk #ff6600 olsun. Menü genişliği 240px. Silme düğmesi asla kırmızı olmasın."}
    filler = [{"role": "user" if i % 2 == 0 else "assistant", "content": "uzun bir ara mesaj " * 100} for i in range(40)]
    out = memory_engine.compact_conversation_context([{"role": "system", "content": "s"}, first, *filler], max_chars=5000)
    summary = out[1]["content"]
    assert "#ff6600" in summary and "240px" in summary and "asla kırmızı" in summary


def test_pins_come_only_from_the_user():
    assert context_pins.pinned([{"role": "assistant", "content": "Ana renk #000000 olsun."}]) == ""


def test_identical_calls_hit_the_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(exact_cache, "_folder", lambda: tmp_path)
    calls = []

    async def chat(system, user, schema):
        calls.append(user)
        return json.dumps({"n": len(calls)})

    ask = exact_cache.cached(chat, "m")

    async def run():
        return [await ask("s", "a", {}), await ask("s", "a", {}), await ask("s", "b", {}), await exact_cache.cached(chat, "other")("s", "a", {})]

    first, again, other, other_model = asyncio.run(run())
    assert first == again and other != first and other_model != first and len(calls) == 3


def test_anonymiser_removes_identifiers_and_never_sends():
    text = "buluta hazırla: ali@firma.com için MerkezFaturaServisi.hesapla_kdv_tutari C:\\musteri\\x.py http://10.0.0.5/api ValueError veriyor, anahtar sk-" + "a" * 30
    reply = escalation.answer(text)
    safe = reply.split("```")[1]
    for leak in ("ali@firma.com", "MerkezFaturaServisi", "hesapla_kdv_tutari", "C:\\musteri", "10.0.0.5", "sk-aaaa"):
        assert leak not in safe
    assert "ValueError" in safe and "Hiçbir yere gönderilmedi" in reply
    assert escalation.answer("anonimlik nedir") == ""


@pytest.mark.parametrize(("text", "extra"), [
    ("devam et", ""), ("devam et ama arayüz İngilizce olsun", "arayüz İngilizce olsun"), ("resume but use sqlite", "use sqlite"),
])
def test_a_resumed_build_can_be_steered(text, extra):
    assert checkpoint.steering(text) == extra
    assert checkpoint.is_resume(text)


def test_ordinary_sentences_are_not_resume_commands():
    assert not checkpoint.is_resume("devam eden işleri listele ama sade olsun")


def test_finished_project_checks_run_together_and_keep_their_order(tmp_path, monkeypatch):
    import time

    import post_checks

    def slow(text):
        def run(*_args):
            time.sleep(0.3)
            return text

        return run

    monkeypatch.setattr(post_checks.security_scan, "report", slow("güvenlik"))
    monkeypatch.setattr(post_checks.visual_audit, "report", slow("görsel"))
    monkeypatch.setattr(post_checks.design_slop, "report", slow(""))
    monkeypatch.setattr(post_checks.package_check, "report", slow("paket"))
    monkeypatch.setattr(post_checks.code_audit, "report", lambda *_: ["kod1", "kod2"])
    monkeypatch.setattr(post_checks.migration_check, "report", slow(""))
    monkeypatch.setattr(post_checks.provenance, "write", lambda *_: None)
    started = time.time()
    done = asyncio.run(post_checks.apply(tmp_path, "bir araç", {"warnings": ["önce"]}))
    assert done["warnings"] == ["önce", "güvenlik", "görsel", "paket", "kod1", "kod2"]
    assert time.time() - started < 1.2  # five 0.3 s checks one after another would need 1.5 s
