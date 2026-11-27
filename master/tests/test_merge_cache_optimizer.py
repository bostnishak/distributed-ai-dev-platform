"""User edits survive a concurrent rewrite; the semantic cache never serves a stale or different answer; prompt rules
are kept only when the measurement improves."""

import asyncio
import importlib.util
from pathlib import Path

import pytest

import merge3
import semantic_cache
import workspace_batches

pytestmark = pytest.mark.unit
_BASE = "def a():\n    return 1\n\n\ndef b():\n    return 2\n"


def test_independent_changes_are_both_kept():
    merged, conflicts = merge3.merge(_BASE, _BASE.replace("return 2", "return 20"), _BASE.replace("return 1", "return 10"), "m.py")
    assert "return 10" in merged and "return 20" in merged and conflicts == []


def test_same_line_keeps_the_users_version_and_says_so():
    merged, conflicts = merge3.merge(_BASE, _BASE.replace("return 1", "return 100"), _BASE.replace("return 1", "return 10"), "m.py")
    assert "return 10\n" in merged and "return 100" not in merged and conflicts == [2]


def test_a_merge_that_breaks_python_falls_back_to_the_user():
    base = "x = [\n    1,\n    2,\n]\ny = 1\n"
    user = base.replace("x = [\n", "x = (\n")
    ai = base.replace("]\n", "]  # son\n")
    merged, conflicts = merge3.merge(base, ai, user, "m.py")
    assert merged == user and conflicts


def test_a_hand_edit_made_during_generation_survives(tmp_path):
    (tmp_path / "m.py").write_text(_BASE, encoding="utf-8")

    async def write(ws_dir, model, spec, ask):
        (tmp_path / "m.py").write_text(_BASE.replace("return 1", "return 10"), encoding="utf-8")  # the user types meanwhile
        code = _BASE.replace("return 2", "return 20")
        (ws_dir / spec["path"]).write_text(code, encoding="utf-8")
        return code

    result = asyncio.run(workspace_batches.apply_edit(write, (tmp_path, "m", "ask"), {"path": "m.py"}, _BASE))
    on_disk = (tmp_path / "m.py").read_text(encoding="utf-8")
    assert "return 10" in on_disk and "return 20" in on_disk and result == on_disk


def test_semantic_cache_is_tied_to_the_document_and_the_numbers(tmp_path, monkeypatch):
    monkeypatch.setattr(semantic_cache, "_path", lambda scope: tmp_path / f"{len(scope)}.json")

    def embed(texts):
        return [[1.0, 0.0] if "kira" in t else [0.0, 1.0] for t in texts]

    semantic_cache.store("belge-1", "2025 kira bedeli nedir", "480000", embed)
    assert semantic_cache.lookup("belge-1", "2025 kira bedeli ne", embed) == "480000"
    assert semantic_cache.lookup("belge-1", "2026 kira bedeli ne", embed) == ""
    assert semantic_cache.lookup("belge-1", "2025 personel sayısı", embed) == ""
    assert semantic_cache.lookup("belge-değişti", "2025 kira bedeli nedir", embed) == ""


def _optimizer():
    spec = importlib.util.spec_from_file_location("optimize_prompt", Path(__file__).resolve().parents[2] / "scripts" / "optimize_prompt.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(("after", "kept"), [([3, 3], True), ([3, 1], False), ([2, 3], False), ([2, 2], False)])
def test_a_rule_stays_only_when_nothing_got_worse(tmp_path, after, kept):
    module = _optimizer()
    prompt = tmp_path / "p.md"
    prompt.write_bytes(b"temel kural\n")
    runs = iter([([3, 2] if after != [3, 3] else [2, 2], ["a: kaldı"]), (after, [])])
    module.optimize(prompt, lambda: next(runs), lambda text, notes: "Her zaman kaynağı belirt ve emin değilsen söyle.")
    assert (b"kaynag" in prompt.read_bytes() or "kaynağı".encode() in prompt.read_bytes()) == kept
    if not kept:
        assert prompt.read_bytes() == b"temel kural\n"
