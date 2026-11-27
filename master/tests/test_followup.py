"""A follow-up carries the request it refers to; a new request stays alone; slash lists are not folders."""

import json

import pytest

import followup
import memory_engine
import workspace_builder

pytestmark = pytest.mark.unit


def _history(*turns):
    return json.dumps([{"role": r, "text": t} for r, t in turns], ensure_ascii=False)


def test_follow_up_chain_keeps_the_original_request():
    history = _history(("user", "OpsControl Lite görev paneli tasarla"), ("assistant", "..."), ("user", "bunu uygulama olarak yap"), ("assistant", "ok"))
    out = followup.merged_request("olmamış, düzelt", history)
    assert out.startswith("OpsControl Lite") and "bunu uygulama olarak yap" in out and "düzelt" in out


def test_new_request_stays_alone():
    history = _history(("user", "bir şiir yaz"), ("assistant", "..."))
    assert followup.merged_request("hesap makinesi uygulaması yap", history) == "hesap makinesi uygulaması yap"
    assert followup.merged_request("bunu pdf yap", "bozuk") == "bunu pdf yap"


def test_last_answer_only_for_follow_ups():
    history = _history(("user", "Ankara hakkında bilgi ver"), ("assistant", "Ankara başkenttir."))
    assert followup.last_answer("bunu pdf yap", history) == "Ankara başkenttir."
    assert followup.last_answer("İzmir hakkında pdf hazırla", history) == ""


def test_old_user_request_survives_compaction():
    spec = "RENK #0F172A " * 100
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": spec}] + [{"role": "assistant", "content": "x" * 8000}] * 6
    assert spec.strip()[:1000] in memory_engine.compact_conversation_context(msgs)[1]["content"]


def test_slash_lists_are_not_folders():
    _, dirs = workspace_builder._extract_requested_paths("Duraklat/Devam Et, Düşük/Orta/Yüksek, Çalışıyor/Bitti ve src/components/ klasörü")
    assert dirs == ["src/components"]
