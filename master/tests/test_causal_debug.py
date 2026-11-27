"""A failing test is repaired only on grounded evidence, and the file is restored when the fix does not work."""

import asyncio
import json

import pytest

import causal_debug

pytestmark = pytest.mark.unit
_LOG = "E   ImportError: cannot import name 'Storage' from 'library'\n1 error in 0.1s"
_BROKEN = "from library import Library, Storage\n\n\ndef test_a():\n    assert Library(Storage()).count() == 0\n"
_FIXED = "from library import Library\nfrom storage import Storage\n\n\ndef test_a():\n    assert Library(Storage()).count() == 0\n"


def _project(root):
    (root / "tests").mkdir()
    (root / "tests" / "test_library.py").write_text(_BROKEN, encoding="utf-8")
    return root / "tests" / "test_library.py"


def _chat(evidence):
    async def chat(system, user, schema):
        return json.dumps({"hypotheses": [{"file": "tests/test_library.py", "evidence": evidence, "cause": "yanlış içe aktarma"}]})

    return chat


def _run(tmp_path, evidence, reply, passes):
    target = _project(tmp_path)
    asked = []

    async def regenerate(rel, ask):
        asked.append(rel)
        return f"```python\n{reply}```"

    def run_tests():
        return "" if passes(target.read_text(encoding="utf-8")) else _LOG

    async def no_patch(system, user):
        return ""

    ok, note = asyncio.run(causal_debug.repair(tmp_path, run_tests, regenerate, causal_debug.Models(_chat(evidence), no_patch), rounds=1))
    return ok, note, target.read_text(encoding="utf-8"), asked


def test_grounded_fix_is_kept(tmp_path):
    ok, note, text, _ = _run(tmp_path, "cannot import name 'Storage' from 'library'", _FIXED, lambda t: "from storage import" in t)
    assert ok and "kök neden" in note and "from storage import Storage" in text


def test_invented_evidence_changes_nothing(tmp_path):
    ok, note, text, asked = _run(tmp_path, "disk is full on drive D", _FIXED, lambda t: "from storage import" in t)
    assert not ok and not asked and text == _BROKEN and "ImportError" in note


def test_fix_that_does_not_pass_is_rolled_back(tmp_path):
    ok, _, text, asked = _run(tmp_path, "cannot import name 'Storage'", _FIXED, lambda t: False)
    assert not ok and asked and text == _BROKEN


def test_deleting_assertions_is_not_a_fix(tmp_path):
    cheat = "from library import Library\n\n\ndef test_a():\n    pass\n"
    ok, _, text, _ = _run(tmp_path, "cannot import name 'Storage'", cheat, lambda t: "Storage" not in t)
    assert not ok and text == _BROKEN


def test_wrong_module_import_is_fixed_without_a_model():
    files = {"library.py": "class Library:\n    pass\n", "storage.py": "class Storage:\n    pass\n",
             "tests/test_library.py": "from library import Library, Storage\n"}
    fixed = causal_debug.fix_imports(_LOG, files)
    assert fixed == {"tests/test_library.py": "from library import Library\nfrom storage import Storage\n"}
    files["other.py"] = "class Storage:\n    pass\n"
    assert causal_debug.fix_imports(_LOG, files) == {}  # two candidates: not certain, leave it to the model
