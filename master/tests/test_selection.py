"""Tests for PB-24: Agent selection algorithm."""

from datetime import UTC, datetime, timedelta

import pytest

from selection import _is_online, score_agent, select_agent


def _make_agent(agent_id: str, context_length: int = 8192, heartbeat_status: str = "idle", last_seen_delta_seconds: int = 5) -> dict:
    last_seen = (datetime.now(UTC) - timedelta(seconds=last_seen_delta_seconds)).isoformat(timespec="seconds")
    return {
        "agent_id": agent_id,
        "context_length": context_length,
        "heartbeat_status": heartbeat_status,
        "last_seen_at": last_seen,
    }


def _fresh_scores(coding=70.0, reasoning=60.0, context=50.0, structured_output=40.0, speed=30.0) -> dict:
    return {
        "coding": coding,
        "reasoning": reasoning,
        "context": context,
        "structured_output": structured_output,
        "speed": speed,
    }


class TestIsOnline:
    def test_recent_agent_is_online(self):
        agent = _make_agent("a1", last_seen_delta_seconds=5)
        assert _is_online(agent) is True

    def test_stale_agent_is_offline(self):
        agent = _make_agent("a1", last_seen_delta_seconds=60)
        assert _is_online(agent) is False

    def test_missing_last_seen_is_offline(self):
        assert _is_online({"agent_id": "a1", "last_seen_at": None}) is False

    def test_exactly_at_threshold_is_offline(self):
        # 30 seconds ago is exactly at the boundary — should be offline (not < 30)
        agent = _make_agent("a1", last_seen_delta_seconds=30)
        assert _is_online(agent) is False


class TestScoreAgent:
    def test_higher_capability_yields_higher_score(self):
        agent = _make_agent("a1")
        scores_high = _fresh_scores(coding=90)
        scores_low = _fresh_scores(coding=10)
        s_high, _ = score_agent(agent, scores_high, "backend")
        s_low, _ = score_agent(agent, scores_low, "backend")
        assert s_high > s_low

    def test_busy_agent_gets_load_penalty(self):
        idle = _make_agent("a1", heartbeat_status="idle")
        busy = _make_agent("a2", heartbeat_status="busy")
        scores = _fresh_scores()
        s_idle, _ = score_agent(idle, scores, "backend")
        s_busy, _ = score_agent(busy, scores, "backend")
        assert s_idle > s_busy

    def test_context_penalty_applied_when_task_exceeds_window(self):
        agent = _make_agent("a1", context_length=4096)
        scores = _fresh_scores()
        s_no_penalty, _ = score_agent(agent, scores, "backend", task_context_tokens=100)
        s_penalty, _ = score_agent(agent, scores, "backend", task_context_tokens=8192)
        assert s_no_penalty > s_penalty

    def test_no_context_penalty_when_task_fits(self):
        agent = _make_agent("a1", context_length=32768)
        scores = _fresh_scores()
        _, breakdown = score_agent(agent, scores, "backend", task_context_tokens=1000)
        assert breakdown["context_penalty"] == 0.0

    def test_breakdown_contains_expected_keys(self):
        agent = _make_agent("a1")
        _, breakdown = score_agent(agent, _fresh_scores(), "backend")
        assert "weighted_capability" in breakdown
        assert "context_penalty" in breakdown
        assert "load_penalty" in breakdown
        assert "final_score" in breakdown

    def test_zero_scores_yields_zero_weighted_capability(self):
        agent = _make_agent("a1")
        scores = _fresh_scores(coding=0, reasoning=0, context=0, structured_output=0, speed=0)
        _, breakdown = score_agent(agent, scores, "backend")
        assert breakdown["weighted_capability"] == 0.0


class TestSelectAgent:
    def test_selects_best_scoring_agent(self):
        agents = [
            _make_agent("a1"),
            _make_agent("a2"),
        ]
        all_scores = {
            "a1": _fresh_scores(coding=90),
            "a2": _fresh_scores(coding=10),
        }
        selected, reason = select_agent("backend", 0, agents, all_scores)
        assert selected == "a1"

    def test_no_online_agents_returns_none(self):
        agents = [_make_agent("a1", last_seen_delta_seconds=120)]
        selected, reason = select_agent("backend", 0, agents, {})
        assert selected is None
        assert "No online agents" in reason["reason"]

    def test_empty_agent_list_returns_none(self):
        selected, reason = select_agent("backend", 0, [], {})
        assert selected is None

    def test_offline_agent_excluded(self):
        online = _make_agent("online", last_seen_delta_seconds=5)
        offline = _make_agent("offline", last_seen_delta_seconds=120)
        all_scores = {
            "online": _fresh_scores(coding=50),
            "offline": _fresh_scores(coding=99),
        }
        selected, _ = select_agent("backend", 0, [online, offline], all_scores)
        # offline has higher capability but should not be selected
        assert selected == "online"

    def test_reason_dict_contains_breakdown(self):
        agents = [_make_agent("a1")]
        _, reason = select_agent("backend", 0, agents, {"a1": _fresh_scores()})
        assert "breakdown" in reason
        assert "selected_agent" in reason

    def test_context_penalty_demotes_small_context_agent(self):
        small_ctx = _make_agent("small", context_length=2048)
        large_ctx = _make_agent("large", context_length=131072)
        scores = {"small": _fresh_scores(coding=80), "large": _fresh_scores(coding=70)}
        # Task needs 10k tokens — small_ctx agent can't handle it well
        selected, _ = select_agent("backend", 10000, [small_ctx, large_ctx], scores)
        assert selected == "large"

    def test_deterministic_selection(self):
        agents = [_make_agent(f"a{i}") for i in range(5)]
        scores = {f"a{i}": _fresh_scores(coding=float(i * 10)) for i in range(5)}
        results = [select_agent("backend", 0, agents, scores)[0] for _ in range(10)]
        assert len(set(results)) == 1  # always same answer
