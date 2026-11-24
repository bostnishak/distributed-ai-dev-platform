"""AJN-02 and F204 persistence: scheduled tasks really run, and F204 state survives a restart."""

import asyncio
from datetime import UTC, datetime

import pytest

import cronjobs
import db
import kvstore


@pytest.fixture(autouse=True)
def _db():
    db.init_db()


def test_cron_parser_accepts_standard_fields_and_rejects_garbage():
    assert cronjobs.parse_cron("*/15 9-17 * * 1-5")[0] == {0, 15, 30, 45}
    for bad in ("", "* * * *", "61 * * * *", "a b c d e", "*/0 * * * *", "5-1 * * * *"):
        with pytest.raises(cronjobs.CronError):
            cronjobs.parse_cron(bad)


def test_cron_matches_uses_cron_weekday_numbering():
    monday_9 = datetime(2026, 11, 23, 9, 0, tzinfo=UTC)  # a Monday
    sunday_9 = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)
    assert cronjobs.cron_matches("0 9 * * 1", monday_9)
    assert not cronjobs.cron_matches("0 9 * * 1", sunday_9)
    assert cronjobs.cron_matches("0 9 * * 0", sunday_9)
    assert not cronjobs.cron_matches("30 9 * * *", monday_9)


def test_due_job_runs_once_per_minute_and_records_the_output():
    job = cronjobs.add_job("rapor", "0 9 * * *", "günlük rapor yaz")
    calls: list[str] = []

    async def runner(prompt: str) -> str:
        calls.append(prompt)
        return "rapor hazır"

    at = datetime(2026, 11, 23, 9, 0, 30, tzinfo=UTC)
    first = asyncio.run(cronjobs.run_due(runner, at))
    second = asyncio.run(cronjobs.run_due(runner, at))
    assert len(first) == 1 and second == []
    assert calls == ["günlük rapor yaz"]
    assert cronjobs.recent_runs(job["id"])[0]["output"] == "rapor hazır"


def test_not_due_job_is_skipped_and_failures_are_recorded_not_raised():
    skipped = cronjobs.add_job("gece", "0 3 * * *", "x")
    broken = cronjobs.add_job("bozuk", "0 9 * * *", "y")

    async def runner(prompt: str) -> str:
        raise RuntimeError("model yok")

    runs = asyncio.run(cronjobs.run_due(runner, datetime(2026, 11, 23, 9, 0, tzinfo=UTC)))
    assert [r["job_id"] for r in runs] == [broken["id"]]
    assert runs[0]["status"] == "error" and "model yok" in runs[0]["output"]
    assert cronjobs.recent_runs(skipped["id"]) == []


def test_state_survives_a_restart_because_it_lives_in_the_database():
    kvstore.PersistentDict("t_dict")["a"] = {"x": 1}
    kvstore.PersistentSet("t_set").add("chat-1")
    kvstore.PersistentList("t_list").append({"q": "ilk"})
    # a brand new object stands in for a freshly started process
    assert kvstore.PersistentDict("t_dict").get("a") == {"x": 1}
    assert "chat-1" in kvstore.PersistentSet("t_set")
    assert list(kvstore.PersistentList("t_list")) == [{"q": "ilk"}]
    kvstore.PersistentSet("t_set").discard("chat-1")
    assert "chat-1" not in kvstore.PersistentSet("t_set")


def test_schedule_endpoints_validate_cron_list_and_delete(client):
    bad = client.post("/api/productivity/agents/schedule", json={"name": "n", "cron": "yarın", "prompt": "p"})
    assert bad.status_code == 422
    ok = client.post("/api/productivity/agents/schedule", json={"name": "n", "cron": "0 9 * * *", "prompt": "p"})
    assert ok.status_code == 200
    listing = client.get("/api/productivity/agents/schedule").json()
    assert [j["id"] for j in listing["jobs"]] == [ok.json()["id"]]
    assert client.delete(f"/api/productivity/agents/schedule/{ok.json()['id']}").status_code == 200
    assert client.delete("/api/productivity/agents/schedule/job_yok").status_code == 404


def test_translate_query_uses_the_model_and_rejects_an_empty_answer(client, monkeypatch):
    import assistant

    async def fake_chat(prompt, system_prompt=None, image_b64=None):
        assert "Target language: en" in prompt and "yapay zeka" in prompt
        return '"artificial intelligence"\nextra', "m"

    monkeypatch.setattr(assistant, "call_ollama_chat", fake_chat)
    res = client.post("/api/productivity/research/translate-query", json={"query": "yapay zeka"})
    assert res.json()["translated"] == "artificial intelligence"

    async def empty_chat(prompt, system_prompt=None, image_b64=None):
        return "  ", "m"

    monkeypatch.setattr(assistant, "call_ollama_chat", empty_chat)
    assert client.post("/api/productivity/research/translate-query", json={"query": "x"}).status_code == 502


def test_drained_agent_gets_no_new_task_even_when_work_is_waiting(client, auth_headers):
    from tests.test_tasks_api import AGENT_PAYLOAD, _create_project_and_task, _register_agent

    _register_agent(client, auth_headers)
    _create_project_and_task()
    agent_id = AGENT_PAYLOAD["agent_id"]
    with db.connect() as conn:
        task_id = conn.execute("SELECT id FROM tasks").fetchone()[0]
        conn.execute("UPDATE tasks SET assigned_to = ? WHERE id = ?", (agent_id, task_id))
    url = f"/api/agents/{agent_id}/tasks/next"
    assert client.get(url, headers=auth_headers).status_code == 200  # work is really waiting
    assert client.post(f"/api/productivity/agents/{agent_id}/drain").status_code == 200
    assert client.get(url, headers=auth_headers).status_code == 204
    client.post(f"/api/productivity/agents/{agent_id}/drain", params={"maintenance_mode": "false"})
    assert client.get(url, headers=auth_headers).status_code == 200


def test_sql_safe_projection_rejects_injection_but_keeps_aggregates():
    import sql_safe

    assert sql_safe.build_select("t", "COUNT(*) AS total_count") == "SELECT COUNT(*) AS total_count FROM \"t\""
    assert sql_safe.build_select("t", 'SUM("x") AS s, COUNT(*) AS n').startswith('SELECT SUM("x") AS s, COUNT(*) AS n')
    for bad in ("1) FROM sqlite_master; --", "COUNT(*) AS a; DROP TABLE t", "x FROM y --", "(SELECT password FROM users)", "name, (SELECT 1)"):
        with pytest.raises(ValueError):
            sql_safe.build_select("t", bad)
