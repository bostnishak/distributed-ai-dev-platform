import asyncio
from types import SimpleNamespace

import pytest

import causal_debug

pytestmark = pytest.mark.unit


def test_empty_critic_answer_falls_back_to_the_writer(monkeypatch):
    """The failure the certification found: the installed reasoning critic returned no text at all."""
    asked = []

    async def critic_for(_writer):
        return "deepseek-r1:8b"

    async def chat(_messages, *, model, **_options):
        asked.append(model)
        return SimpleNamespace(content="" if model.startswith("deepseek") else "{}")

    monkeypatch.setattr(causal_debug.critic_models, "critic_for", critic_for)
    monkeypatch.setattr(causal_debug.gateway.default_client, "chat", chat)
    assert asyncio.run(causal_debug._ask("s", "u", {})) == "{}"
    assert asked == ["deepseek-r1:8b", "qwen3.5:9b"]


def test_a_source_quote_counts_and_the_source_file_is_repaired_before_the_test_file():
    files = {"calc.py": "for price in prices[1:]:", "test_calc.py": "assert total([1, 2, 3]) == 6"}
    guess = causal_debug.Hypothesis
    audit = causal_debug.Audit(hypotheses=[guess(file="test_calc.py", evidence="assert 5 == 6", cause="t"),
                                           guess(file="calc.py", evidence="for price in prices[1:]:", cause="c"),
                                           guess(file="calc.py", evidence="uydurma bir satır", cause="x")])
    assert [h.cause for h in causal_debug.grounded(audit, "E assert 5 == 6", files)] == ["c", "t"]
