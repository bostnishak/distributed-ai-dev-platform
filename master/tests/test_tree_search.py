"""Tree search builds on partial progress and is bounded."""

import asyncio

import pytest

import causal_debug
import tree_search

pytestmark = pytest.mark.unit


def _score(files):
    async def run():
        return sum(files["x"].count(ch) > 0 for ch in "abc") / 3

    return run()


def test_partial_fixes_are_combined_into_a_full_one():
    async def expand(files):
        return [{"x": files["x"] + ch} for ch in "zab c".replace(" ", "")]

    best, score, tried = asyncio.run(tree_search.search({"x": ""}, expand, _score, budget=20))
    assert score == 1.0 and all(ch in best["x"] for ch in "abc") and tried <= 20


def test_budget_ends_a_hopeless_search():
    calls = []

    async def expand(files):
        calls.append(1)
        return [{"x": files["x"] + "z"}]

    best, score, tried = asyncio.run(tree_search.search({"x": ""}, expand, _score, budget=4))
    assert score == 0 and best == {"x": ""} and tried <= 4 and len(calls) <= 5


def test_nothing_to_propose_terminates():
    async def expand(files):
        return []

    assert asyncio.run(tree_search.search({"x": "a"}, expand, _score, budget=3))[1] == pytest.approx(1 / 3)


@pytest.mark.parametrize(("output", "value"), [("3 passed in 0.1s", 1.0), ("1 failed, 3 passed in 1s", 0.75), ("2 errors in 1s", 0.0), ("", 1.0)])
def test_share_of_passing_tests(output, value):
    assert causal_debug.pass_share(output) == pytest.approx(value)
