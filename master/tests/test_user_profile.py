"""Personal space: profiles, settings validation, usage statistics, cross-chat memory and API."""

from __future__ import annotations

import json

import pytest

import config
import memory_engine
import user_profile as up

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)


def test_default_profile_and_settings_validation():
    prof = up.get_profile("default")
    assert prof["settings"]["theme"] == "system"
    updated = up.update_profile(
        "default",
        display_name="Ayse Demir",
        settings={"theme": "dark", "accent": "neon", "font_size": "large", "reduce_motion": "yes", "bogus": 1},
    )
    assert updated["display_name"] == "Ayse Demir"
    assert updated["settings"]["theme"] == "dark"
    assert updated["settings"]["font_size"] == "large"
    # invalid enum, wrong bool type and unknown keys are ignored
    assert updated["settings"]["accent"] == "indigo"
    assert updated["settings"]["reduce_motion"] is False
    assert "bogus" not in updated["settings"]


def test_profiles_are_isolated_and_default_cannot_be_deleted():
    other = up.create_profile("Kalite Birimi")
    assert other["user_id"] == "kalite-birimi"
    up.update_profile(other["user_id"], settings={"tone": "friendly"})
    assert up.get_settings("default")["tone"] == "professional"
    assert up.get_settings("kalite-birimi")["tone"] == "friendly"
    up.delete_profile("kalite-birimi")
    assert {p["user_id"] for p in up.list_profiles()} == {"default"}
    with pytest.raises(ValueError):
        up.delete_profile("default")
    with pytest.raises(ValueError):
        up.valid_user_id("../etc")


def test_usage_summary_totals_budget_and_streak():
    up.update_profile("default", settings={"monthly_token_budget": 1000})
    up.record_usage("default", "c1", "qwen3.5:9b", "genel", 100, 400, 2000)
    up.record_usage("default", "c1", "qwen3.5:9b", "kod", 50, 150, 4000)
    up.record_usage("default", "c2", "cnc-ballooner", "cnc", 10, 20, 1000, estimated=True)
    s = up.usage_summary("default", days=7)
    assert s["totals"]["messages"] == 3
    assert s["totals"]["total_tokens"] == 730
    assert s["totals"]["conversations"] == 2
    assert s["totals"]["avg_latency_ms"] == round(7000 / 3)
    assert s["totals"]["streak_days"] == 1
    assert len(s["daily"]) == 7 and s["daily"][-1]["tokens"] == 730
    assert s["by_model"][0]["model"] == "qwen3.5:9b"
    assert s["budget"]["percent"] == 73.0
    # other profiles never see this usage
    assert up.usage_summary("someone-else")["totals"]["messages"] == 0


def test_personalization_block_reflects_settings():
    up.update_profile(
        "default",
        display_name="Mehmet",
        role_title="CNC Mühendisi",
        settings={"response_style": "concise", "expertise_level": "expert", "custom_instructions": "Hep mm kullan."},
    )
    block = up.personalization_block("default")
    assert "Mehmet" in block and "CNC Mühendisi" in block
    assert "kisa" in block and "uzman" in block and "Hep mm kullan." in block


def test_cross_chat_search_is_scoped_to_user_and_excludes_current_chat():
    memory_engine.record_conversation_turn("chat-a", "Flans icin H7 tolerans nedir", "H7 delik toleransi 21 mikron", user_id="default")
    memory_engine.record_conversation_turn("chat-b", "Baska bir flans sorusu", "cevap", user_id="default")
    memory_engine.record_conversation_turn("chat-x", "Flans tolerans gizli", "baska kullanici", user_id="other")
    hits = up.cross_chat_snippets("default", "flans tolerans", exclude_conversation="chat-b")
    ids = {h["conversation_id"] for h in hits}
    assert "chat-a" in ids
    assert "chat-b" not in ids and "chat-x" not in ids
    assert "H7" in up.cross_chat_context_block("default", "H7 tolerans", exclude_conversation="chat-z")


def test_record_turn_can_skip_fact_learning():
    memory_engine.record_conversation_turn("c1", "Bizim malzeme AISI 4140", "tamam", user_id="default", learn=False)
    assert memory_engine.list_semantic_facts(user_id="default") == []
    memory_engine.record_conversation_turn("c2", "Bizim malzeme AISI 4140", "tamam", user_id="default", learn=True)
    assert memory_engine.list_semantic_facts(user_id="default")


def test_wipe_and_export():
    up.record_usage("default", "c1", "m", "genel", 1, 2, 10)
    memory_engine.record_conversation_turn("c1", "FastAPI kullaniyoruz", "ok", user_id="default")
    exported = up.export_all("default")
    assert exported["usage"]["totals"]["messages"] == 1
    assert exported["conversations"][0]["messages"][0]["role"] == "user"
    removed = up.wipe_data("default", "all")
    assert removed["usage"] == 1 and removed["conversations"] == 1 and removed["memories"] >= 1
    assert up.usage_summary("default")["totals"]["messages"] == 0
    assert up.cross_chat_snippets("default", "FastAPI") == []
    with pytest.raises(ValueError):
        up.wipe_data("default", "everything")


def test_user_api_roundtrip(client):
    assert client.get("/api/user/default/profile").json()["display_name"] == "Kullanici"
    r = client.put("/api/user/default/profile", json={"display_name": "Zeynep", "settings": {"theme": "dark", "accent": "teal"}})
    assert r.status_code == 200 and r.json()["settings"]["accent"] == "teal"
    assert client.get("/api/user/BAD..ID/profile").status_code in (400, 404)
    created = client.post("/api/user/profiles", json={"display_name": "Ekip"}).json()
    assert created["user_id"] == "ekip"
    assert {p["user_id"] for p in client.get("/api/user/profiles").json()["profiles"]} == {"default", "ekip"}
    assert client.delete("/api/user/default").status_code == 400
    added = client.post("/api/user/default/memories", json={"category": "preference", "fact_value": "Olculer mm olsun"})
    assert added.status_code == 200
    mems = client.get("/api/user/default/memories").json()["memories"]
    assert mems and client.delete(f"/api/user/default/memories/{mems[0]['id']}").status_code == 200
    assert client.delete("/api/user/default/memories/99999").status_code == 404
    exported = client.get("/api/user/default/export")
    assert exported.status_code == 200 and "attachment" in exported.headers["content-disposition"]
    assert json.loads(exported.text)["profile"]["display_name"] == "Zeynep"
    assert client.delete("/api/user/default/data?scope=nope").status_code == 400


def test_chat_stream_records_usage_and_turn(client):
    r = client.post(
        "/api/assistant/chat/stream",
        data={"prompt": "125*4 kaç eder", "user_id": "default", "conversation_id": "chat-test-1"},
    )
    assert r.status_code == 200
    done = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ") and '"done"' in line][-1]
    assert done["usage"]["estimated"] is True
    assert done["latency_ms"] >= 0
    stats = client.get("/api/user/default/stats?days=7").json()
    assert stats["totals"]["messages"] == 1
    assert stats["by_task"][0]["task_type"] == "hesaplama"
    convs = client.get("/api/user/default/conversations").json()["conversations"]
    assert convs and convs[0]["id"] == "chat-test-1"
    bad = client.post("/api/assistant/chat/stream", data={"prompt": "2+2", "user_id": "../x"})
    assert bad.status_code == 400


def test_saved_chats_disk_persistence_roundtrip(client):
    payload = {
        "title": "CNC Flans Sohbeti",
        "updatedAt": 1700000000000,
        "messages": [
            {"role": "user", "text": "AISI 4140 flans toleransi"},
            {"role": "assistant", "text": "H7/g6 gecme onerilir.", "modelBadge": "cnc-ballooner"},
        ],
    }
    put_resp = client.put("/api/user/default/chats/chat_persisted_1", json=payload)
    assert put_resp.status_code == 200
    get_resp = client.get("/api/user/default/chats")
    assert get_resp.status_code == 200
    chats = get_resp.json()["chats"]
    assert "chat_persisted_1" in chats
    assert chats["chat_persisted_1"]["title"] == "CNC Flans Sohbeti"
    assert len(chats["chat_persisted_1"]["messages"]) == 2
    del_resp = client.delete("/api/user/default/chats/chat_persisted_1")
    assert del_resp.status_code == 200
    assert "chat_persisted_1" not in client.get("/api/user/default/chats").json()["chats"]

